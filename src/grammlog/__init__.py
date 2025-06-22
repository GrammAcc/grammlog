"""Pure python package that provides structured logging to JSONL with no dependencies.

Supports asynchronous logging via asyncio. See: [Asynchronous Logging](#asynchronous-logging)

Provides wrappers around the standard `debug`, `info`, `warning`, `error`, and `critical`
functions.

Each function accepts a [`Logger`](https://docs.python.org/3/library/logging.html#logging.Logger)
as its first argument, so you can provide a custom logger with your own handlers to write
structured logs to any target.

This package also provides a `make_logger` convenience function that creates and configures
a file-based logger with rotating log files and a size limit.

## Installation

```bash
pip install grammlog
```

## Basic Usage

```pycon
>>> import os
>>> import grammlog
>>> logger = grammlog.make_logger("app", log_dir="logs", log_level=grammlog.Level.INFO)
>>> grammlog.info(logger, "application initialized")
>>> grammlog.info(
...     logger,
...     "env vars set",
...     {"env": os.environ},
... )
>>> grammlog.set_env(grammlog_dir="logs", default_grammlog_level=grammlog.Level.INFO)
>>> auth_log = grammlog.make_logger("auth")  # Use the log_dir and log_level from the env.
>>> try:
...     user_id = 42
...     get_user_if_logged_in(user_id)
... except NameError as e:
...     grammlog.error(
...         logger,
...         "User was not logged in",
...         {"user_id": user_id},
...         err=e,
...     )
>>> db_logger = grammlog.make_logger(
...     "db_queries", log_dir="logs/db", log_level=grammlog.Level.ERROR
... )
>>> try:
...     user_name = "invalid"
...     db.query(table="users", user_name=user_name)
... except NameError as e:
...     grammlog.error(
...         db_logger,
...         "Unknown error in db query",
...         {"queried_table": "users", "user_name": user_name},
...         err=e,
...     )

```

## Structured Data

The logging functions all take an arbitrary logger as their first argument, which
allows them to output structured logs to any handlers supported by the stdlib's logging module.
But they also accept a required string `msg`, and an optional `details` dictionary as well as
an optional `err` Exception.

These arguments will be merged together into a JSON-formatted object that will be serialized
and written to a single line of JSONL logged output using the provided logger.

In addition to the data provided in the function arguments, the logged object will also include
the following keys:

  - `level`: The logging level of the message. E.g. 'DEBUG', 'ERROR'.
  - `timestamp`: The timestamp of the logging event in UTC as given by
[`datetime.datetime.timestamp()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.timestamp)


If the `err` argument is not `None`, then the logged line will also contain the following keys:

  - `err`: The `repr` of the `err` object.
  - `traceback`: The formatted traceback of the exception.

The `msg` string will be merged into the object under the `msg` key, and all keys and values
in the `details` dict will be merged into the resulting object as-is.

The keys in the `details` dict are assumed to be strings, but the values can be any type.
If a value is not json-serializable, the logging function will force a string conversion
by calling `str(value)` on it. This is applied recursively to any nested dictionaries as well.

The default of calling `str` on the values is fine for logging blobs of dictionary data, but
usually, it's best to explicitly convert an unsupported value to a json-serializable form before
logging it so that the logs contain all of the information expected. For example, when logging
dates/datetimes, it may be desirable to have a very high precision POSIX timestamp, or you may
want to log a more human-readable ISO-formatted date string. Converting the value to the desired
format before logging it is preferred.

### Processing Structured Logs

Logging in a structured format like JSON is useful because we can query the logs
based on keys and values instead of simply scanning through thousands of lines
of text manually or with inaccurate search heuristics.

For example, using the shell tool [`jq`](https://jqlang.github.io/jq/), we can
filter our logs to only the lines that have an `err` object logged.

    cat debug.log | jq 'select(.err != null)'

Or we can get a list of all log entries from the last 42 minutes.

    cat debug.log | jq 'select(.timestamp >= (now - 2520))'

Or we can count the number of log entries.

    cat debug.log | jq --slurp 'length'

Or we can get an array of (msg, traceback) tuples for all of the ValueErrors that we've logged.

    cat debug.log | jq 'select(.err != null) | select(.err | contains("ValueError")) | \
[.msg, .traceback]'

Or we can use any other combination of query-like filters to examine the exact
messages we're concerned with.

This means that if we include queryable keys in our logging calls in the source code, it is
easy to find the specific error messages we need to debug all the nasty issues our applications
give us at 3am on a Saturday.

## Asynchronous Logging

There are async versions of each of the logging functions as well as
`register_async_logger` and `deregister_async_logger` functions:

- `async_debug`
- `async_info`
- `async_warning`
- `async_error`
- `async_critical`
- `register_async_logger`
- `deregister_async_logger`
- `flush`

The async logging functions need the logger to be registered to an async queue.
This is because the logging calls themselves are synchronous, and they
need to be queued in order to run them concurrently with other tasks in the event
loop. Registering a logger to be used asynchronously doesn't mutate the logger in
any way, and *async loggers* are still the same
[`logging.Logger`](https://docs.python.org/3/library/logging.html#logging.Logger)
objects. Calling `register_async_logger` simply creates an
[`asyncio.Queue`](https://docs.python.org/3/library/asyncio-queue.html#asyncio.Queue)
and a [`Task`](https://docs.python.org/3/library/asyncio-task.html#task-object)
to run synchronous logging functions in the background.

For convenience, a queue will be registered for the logger when calling any of the `async_*`
functions if one is not already registered. This makes environments like async unit tests
that may be overriding or mocking event loops more reliable, but it makes it easy to miss
an implicit queue registration. This can be problematic in applications that use multiple
event loops, but for most applications, it's safe to let the `async_*` functions handle
queue registration and simply call `flush` when shutting down the application.

The async queues are managed internally in this package and run the logging
events on the event loop in the background. This means that a call like
`await async_info(logger, msg)` doesn't actually wait until the message is logged;
it puts an event into the queue to be logged in the background at the discretion of
the event loop's task scheduler. This means that `deregister_async_logger` needs to
be called on any loggers registered as async before application shutdown in order to
guarantee all log messages are flushed to their targets. Failing to deregister a
logger will not cause any problems, but it may result in pending log messages being
lost. To simplify cleanup, the `flush` function can be used to
deregister all registered async loggers during the application's shutdown procedure
without needing a reference to each individual logger in that scope.

Similarly to how any logger with any handlers can be used with the sync functions
for structured logging to any target, any logger can be registered as an async logger by passing
it into the `register_async_logger` function. That does not mean that registering another library's
logger will cause that library's logging events to run asynchronously. The asynchronous logging only
works if the `async_*` functions are used. Registering a logger that you don't control will only add
overhead due to the empty task taking CPU cycles away from other background work on the event loop.

### Flask/Quart asyncio example

Example:
```python
    #  __init__.py

    from quart import Quart

    import grammlog

    def create_app():
        app = Quart()

        @app.before_serving
        async def register_async_loggers():
            # These loggers will be registered to the same event loop
            # that the production server (e.g. hypercorn) is running.

            grammlog.register_async_logger(grammlog.make_logger("auth"))
            grammlog.register_async_logger(grammlog.make_logger("error"))

        @app.after_serving
        async def flush_pending_log_messages():
            await grammlog.flush()

        return app

    # file.py
    from Quart import Response

    import grammlog

    # This returns the same logger that was registered
    # in the app factory.
    auth_log = grammlog.make_logger("auth")

    my_user_id = 1

    async def authenticate(user_id):
        if user_id != my_user_id:
            await grammlog.async_error(auth_log, "Super secure authentication failed!")
            return Response(401)
        else:
            return Response(200)
```


### Async Performance Considerations

Using async logging won't make your logging any faster. Because writing the actual log messages
is synchronous, excessive logging will still cause a CPU-bound bottleneck in your application.
However, if you are using asyncio already, using async logging should make your code more efficient
by giving the event loop a chance to start other background tasks in between registering a logging
event and actually logging the message. In other words, the main benefit is not to make logging more
efficient but instead to make sure the event loop can keep as many concurrent tasks running as
possible.

One thing to consider with respect to the async event loop is the size limit for the logging
queues. The queues will not block the event loop from
running other tasks regardless of the size limit, but there are tradeoffs to consider.
Due to the way
[`asyncio.Queue`](https://docs.python.org/3/library/asyncio-queue.html#asyncio.Queue)
works, when the queue is full, it will continue to pass execution to other tasks until
an item is removed from the queue. This means that in situations where the application is
performing excessive logging due to some unforseen usage pattern or a programming oversight, the
size limit on the queue will help to throttle the CPU usage of the logging events by not continuing
to enqueue more events until the oldest one is evicted. This will give the event loop more chances
to start other tasks such as handling a request through the web framework or sending an async API
response to the frontend. The logging events will still hog the CPU while they are running, but
the size limit maximizes the chances the application has to start other IO-bound tasks in between
logging events. The flipside of this is that if the async logging call is happening inside a handler
for a request or before sending a response to the client, then that entire coroutine will wait until
there is space in the queue to add another logging event. For this reason, some applications may
want to use a large size limit for logging queues depending on their needs, but it is very unlikely
that the wait time for a queue eviction would result in a more significant slowdown than the CPU
load that an unbounded queue would allow the logging events to accumulate.

When in doubt, profile.
"""

import asyncio
import datetime
import json
import logging
import os
import traceback
from enum import IntEnum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import (
    Any,
    Protocol,
)

__VERSION__ = "1.3.0"


_string_to_log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_log_level_to_string_map = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class Level(IntEnum):
    """The stdlib `logging` levels are module-level constants, but there
    is no containing type or enum for them, so type annotations and documentation
    is annoying. This enum wraps the stdlib's logging levels for easier documentation
    and type checking."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def set_env(grammlog_dir: str | Path, default_grammlog_level: Level) -> None:
    """Explicitly set the `GRAMMLOG_DIR` and `DEFAULT_GRAMMLOG_LEVEL` env vars without
    loading them from a file.

    Overwrites the `GRAMMLOG_DIR` and `DEFAULT_GRAMMLOG_LEVEL` vars in the global environment.
    See: [`os.environ`](https://docs.python.org/3/library/os.html#os.environ)
    """

    os.environ["GRAMMLOG_DIR"] = str(Path(grammlog_dir))
    os.environ["DEFAULT_GRAMMLOG_LEVEL"] = _log_level_to_string_map[default_grammlog_level]


def make_logger(
    log_name: str,
    size_limit: int = 1024 * 1024 * 4,
    log_dir: str | Path | None = None,
    log_level: Level | None = None,
) -> logging.Logger:
    """Create and return a rotating file-based logger.

    This function is idempotent.

    Uses [`getLogger`](https://docs.python.org/3/library/logging.html#logging.getLogger)
    to register/retrieve the logger and adds a
    [`RotatingFileHandler`](https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler)
    with four rotating backups if one has not been registered already.

    Args:
        log_name:
            The logger name passed to `getLogger`. Also determines the log filename.
            The log files for this logger will be written to `{log_dir}/{log_name}.log`.
        size_limit:
            The total size limit for this logger in bytes.
            This value will be divided by 4 to give the size of each rotating log file.
            Default is 1024 * 1024 * 4 (~4mb), which gives four rotating 1mb log files.
            The default size limits are fairly small since this is a per-logger value.
            Be careful when using a large `size_limit` if you create several different
            loggers. Especially if you are in a server environment.
        log_dir:
            The parent directory to store the rotating log files.
            If `None` or not provided, then this value will be read from the `GRAMMLOG_DIR`
            environment variable.
            The directory is created if it does not exist.
        log_level:
            The logging level to set this logger to.
            If `None` or not provided, then this value will be read from the `GRAMMLOG_LEVEL`
            environment variable if it is present with fallback to the `DEFAULT_GRAMMLOG_LEVEL`
            environment variable.
            This allows complex applications such as web servers to use a default logging
            configuration with the ability to override the level on the commandline.
            For example, the application could read a `.env` file with

                DEFAULT_GRAMMLOG_LEVEL=ERROR

            in production but have a cronjob with

                @daily GRAMMLOG_LEVEL=INFO python scheduled_maintenance_script.py

            so that more information is logged for the scheduled maintenance tasks
            compared to the regular application usage.
    Raises:
        RuntimeError:
            If
              - `log_dir` is not provided or is `None` and `GRAMMLOG_DIR` is not in the env.
              - `log_level` is not provided or is `None` and `DEFAULT_GRAMMLOG_LEVEL` is not
                in the env.
    Returns:
        The newly created or previously configured Logger instance.
    """

    # TODO: This function is intended to be idempotent, but the logic of the
    # handler setup is not. If a caller calls this function with the same `logger_name`, but
    # different `size_limit`s then the second call will return the first logger unchanged.
    # I need to think about how I want to resolve this. The current behavior is probably fine
    # since this is just a convenience function, so changing a handler should probably be
    # done manually. But I still need to put some thought into this and at least document this
    # behavior more clearly.

    if log_dir is None:
        if "GRAMMLOG_DIR" not in os.environ:
            raise RuntimeError("Missing env var: 'GRAMMLOG_DIR'.")
        log_dir = Path(os.environ["GRAMMLOG_DIR"])
    else:
        log_dir = Path(log_dir)
    if log_level is None:
        if "DEFAULT_GRAMMLOG_LEVEL" not in os.environ:
            raise RuntimeError("Missing env var: 'DEFAULT_GRAMMLOG_LEVEL'.")
        log_level_str = os.environ.get("GRAMMLOG_LEVEL", os.environ["DEFAULT_GRAMMLOG_LEVEL"])
        logging_level = _string_to_log_level_map[log_level_str]
    else:
        logging_level = log_level.value

    if not log_dir.exists():
        log_dir.mkdir(parents=True)

    logger = logging.getLogger(log_name)
    logger.setLevel(logging_level)

    if not logger.handlers:
        log_handler = RotatingFileHandler(
            filename=log_dir / f"{log_name}.log",
            mode="a",
            encoding="utf-8",
            maxBytes=int(size_limit / 4),
            backupCount=4,
        )
        log_handler.setLevel(logging_level)
        logger.addHandler(log_handler)

    return logger


def _ensure_serializable(payload: dict[str, Any]) -> dict[str, str | dict]:
    # Convert non-json serializable values to strings.
    # This is recursive, so it could fail if the provided dict is deeply nested.
    # This should only happen if the application exposes logging to user-input and
    # allows a user to construct a malicious payload.

    # TODO: There is a bug in this implementation.
    # It currently calls `str` on *all* values in the payload when json serialization fails, but
    # it should only call `str` on values that are not serializable.
    # This can cause problems when parsing the logged data in other environments if an integer gets
    # serialized as a string for example.
    return {
        k: (_ensure_serializable(v) if isinstance(v, dict) else str(v)) for k, v in payload.items()
    }


def _jsonify(payload: dict[str, Any]) -> str:
    try:
        return json.dumps(payload)
    except TypeError:
        return json.dumps(_ensure_serializable(payload))


def _build_entry(
    level: str,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
    *,
    timestamp_override: datetime.datetime | None = None,
) -> str:
    # Construct the actual structured log line.

    payload = {"msg": msg, **details}

    payload["timestamp"] = (
        datetime.datetime.now(datetime.timezone.utc).timestamp()
        if timestamp_override is None
        else timestamp_override.timestamp()
    )
    payload["level"] = level
    if err is not None:
        payload["err"] = repr(err)
        payload["traceback"] = "".join(traceback.format_exception(err))
    return _jsonify(payload)


def _debug(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
    *,
    timestamp_override: datetime.datetime | None = None,
) -> None:

    entry = _build_entry("DEBUG", msg, details, err, timestamp_override=timestamp_override)
    logger.debug(entry)


def debug(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Wraps the
    [`logging.Logger.debug`](https://docs.python.org/3/library/logging.html#logging.Logger)
    function to write a JSON-formatted string instead of the default text format.

    Each call to this function will write a single JSON object as a new line in the log file.
    (JSONL)

    Args:
        See: [Structured Data](#structured-data)
    """

    _debug(logger, msg, details, err)


def _info(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
    *,
    timestamp_override: datetime.datetime | None = None,
) -> None:

    entry = _build_entry("INFO", msg, details, err, timestamp_override=timestamp_override)
    logger.info(entry)


def info(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Wraps the
    [`logging.Logger.info`](https://docs.python.org/3/library/logging.html#logging.Logger)
    function to write a JSON-formatted string instead of the default text format.

    Each call to this function will write a single JSON object as a new line in the log file.
    (JSONL)

    Args:
        See: [Structured Data](#structured-data)
    """

    _info(logger, msg, details, err)


def _warning(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
    *,
    timestamp_override: datetime.datetime | None = None,
) -> None:

    entry = _build_entry("WARNING", msg, details, err, timestamp_override=timestamp_override)
    logger.warning(entry)


def warning(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Wraps the
    [`logging.Logger.warning`](https://docs.python.org/3/library/logging.html#logging.Logger)
    function to write a JSON-formatted string instead of the default text format.

    Each call to this function will write a single JSON object as a new line in the log file.
    (JSONL)

    Args:
        See: [Structured Data](#structured-data)
    """

    _warning(logger, msg, details, err)


def _error(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
    *,
    timestamp_override: datetime.datetime | None = None,
) -> None:

    entry = _build_entry("ERROR", msg, details, err, timestamp_override=timestamp_override)
    logger.error(entry)


def error(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Wraps the
    [`logging.Logger.error`](https://docs.python.org/3/library/logging.html#logging.Logger)
    function to write a JSON-formatted string instead of the default text format.

    Each call to this function will write a single JSON object as a new line in the log file.
    (JSONL)

    Args:
        See: [Structured Data](#structured-data)
    """

    _error(logger, msg, details, err)


def _critical(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
    *,
    timestamp_override: datetime.datetime | None = None,
) -> None:

    entry = _build_entry("CRITICAL", msg, details, err, timestamp_override=timestamp_override)
    logger.critical(entry)


def critical(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Wraps the
    [`logging.Logger.critical`](https://docs.python.org/3/library/logging.html#logging.Logger)
    function to write a JSON-formatted string instead of the default text format.

    Each call to this function will write a single JSON object as a new line in the log file.
    (JSONL)

    Args:
        See: [Structured Data](#structured-data)
    """

    _critical(logger, msg, details, err)


_QUEUES: dict[str, tuple[asyncio.Task, asyncio.Queue]] = {}


async def _logging_loop(q: asyncio.Queue) -> None:
    # This is where all the magic happens. :)
    # This coroutine is intended to be wrapped in a task, so that logging events can
    # be run in the background.
    # The `async_*` logging functions will `put` a (func, args, kwargs) tuple into
    # the queue, so that `q.get()` will block until a call to one of the async logging
    # functions with the logger that this queue is for.
    # The infinite loop will break when the wrapping task is cancelled due to the
    # asyncio.CancelledError being raised.

    while True:
        func, args, kwargs = await q.get()
        func(*args, **kwargs)


def register_async_logger(logger: logging.Logger, max_size: int = 10) -> logging.Logger:
    """Create an async queue for the provided `logger`.

    Creates a new
    [`asyncio.Queue`](https://docs.python.org/3/library/asyncio-queue.html#asyncio.Queue)
    to handle asynchronous logging events.

    Calls to the async logging functions e.g. `await async_debug(logger, msg)` will
    still perform blocking IO when actually writing to the log file, but by running
    logging events in an async queue, we give the event loop a chance to start other
    tasks in the background before we lock up the CPU for writing.

    Args:
        logger:
            The logger to create a new queue for.
        max_size:
            This is the size limit of the queue. It is passed directly to
            the constructor for
            [`asyncio.Queue`](https://docs.python.org/3/library/asyncio-queue.html#asyncio.Queue),
            so to create an unbounded queue, pass a value <= 0.
            Note that you probably don't want to create an unbounded queue.
            See: [Async Performance Considerations](#async-performance-considerations) for details.
    Raises:
        ValueError:
            If a queue has already been registered for this logger.
            To register a different queue for the same logger, e.g. to change the
            queue size, you must explicitly call

                await deregister_async_logger(logger)

            first. Otherwise, pending logging events may be lost.
        RuntimeError:
            If not called from within a running event loop.
            Even though this is a synchronous function, it creates an async
            task in the running loop, so it can only be called from within
            a running event loop e.g. a coroutine.
    Returns:
        The `logger` unchanged.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        raise RuntimeError("register_async_logger requires a running event loop.") from None

    logger_name = logger.name
    if logger_name in _QUEUES:
        raise ValueError(
            f"Logger {logger_name} already registered to an async queue. \
If you intended to update the queue size, you must explicitly `deregister_async_logger` \
before calling this function to register the new queue."
        )

    q: asyncio.Queue = asyncio.Queue(maxsize=max_size)
    task = asyncio.create_task(_logging_loop(q))
    _QUEUES[logger.name] = task, q
    return logger


async def _deregister(logger_name: str) -> None:
    # Remove logger with `logger_name` from the `_QUEUES` registry.
    # `logger_name` is assumed to exist in the `_QUEUES` registry, so if `logger_name`
    # is user-provided, it needs to be checked before calling this function.

    task, q = _QUEUES[logger_name]
    # We remove the queue before we cancel and cleanup the task
    # because we want to ensure that all pending log messages are
    # flushed, and if we flush the current queue before deleting it
    # from the `_QUEUES` registry, then we could have a race condition
    # where an async logging function is called in another coroutine
    # between the flush and the delete, which would result in that
    # message being lost.
    del _QUEUES[logger_name]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # Flush remaining log events from the queue.
        while not q.empty():
            func, args, kwargs = await q.get()
            func(*args, **kwargs)


async def deregister_async_logger(logger: logging.Logger) -> logging.Logger:
    """Removes a previously registered async queue for `logger`.

    This function must be called before terminating the running python process
    to ensure that any logging events that have been queued and not executed yet are
    completed. Failing to await this function before closing an application won't cause
    any problems, but pending log messages may be lost.

    Raises:
        ValueError:
            If a queue is not registered for this logger.
    Returns:
        The `logger` unchanged.
    """

    logger_name = logger.name
    if logger_name not in _QUEUES:
        raise ValueError(
            f"Logger {logger_name} is not registered to an async queue. \
Did you mean to call `register_async_logger`?"
        )

    await _deregister(logger_name)
    return logger


async def flush() -> None:
    """Calls `deregister_async_logger` on all registered loggers.

    This can be used to cleanup resources before application shutdown without
    needing to keep a reference to every logger in the application.

    Example:
        >>> import asyncio
        >>> import grammlog
        >>> loggers = [
        ...     grammlog.make_logger(
        ...         f"async_{name}", log_dir="logs", log_level=grammlog.Level.DEBUG
        ...     )
        ...     for name in ["some", "variable", "list"]
        ... ]
        >>> async def log_stuff():
        ...     for logger in loggers:
        ...         grammlog.register_async_logger(logger)
        ...     await grammlog.async_debug(loggers[0], "some message")
        >>> async def shutdown():
        ...     await grammlog.flush()
        >>> async def main():
        ...     await log_stuff()
        ...     await shutdown()
        >>> asyncio.run(main())
    """

    logger_names = [i for i in _QUEUES.keys()]  # Copy.
    for logger_name in logger_names:
        await _deregister(logger_name)


class _SyncLogFunc(Protocol):

    def __call__(
        self,
        logger: logging.Logger,
        msg: str,
        details: dict[str, Any],
        err: BaseException | None = None,
        *,
        timestamp_override: datetime.datetime | None = None,
    ) -> None: ...


async def _async_log_event(
    sync_log_func: _SyncLogFunc,
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    err: BaseException | None = None,
) -> None:

    logger_name = logger.name
    if logger_name not in _QUEUES:
        register_async_logger(logger)

    _, q = _QUEUES[logger_name]
    func, args, kwargs = (
        sync_log_func,
        [logger, msg, details],
        {"err": err, "timestamp_override": datetime.datetime.now(datetime.timezone.utc)},
    )
    logging_event = func, args, kwargs

    await q.put(logging_event)


async def async_debug(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Enqueue an asynchronous debug logging event.

    This function registers a future call to `debug` to the async queue to be scheduled on the
    event loop.

    Calls `register_async_logger` with the provided `logger` instance
    if no queue is registered for this logger in the running event loop.
    This means the implicitly created queue will have the default queue size.

    All arguments are passed to the sync `debug` function as is.
    """

    await _async_log_event(_debug, logger, msg, details, err)


async def async_info(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Enqueue an asynchronous info logging event.

    This function registers a future call to `info` to the async queue to be scheduled on the
    event loop.

    Calls `register_async_logger` with the provided `logger` instance
    if no queue is registered for this logger in the running event loop.
    This means the implicitly created queue will have the default queue size.

    All arguments are passed to the sync `info` function as is.
    """

    await _async_log_event(_info, logger, msg, details, err)


async def async_warning(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Enqueue an asynchronous warning logging event.

    This function registers a future call to `warning` to the async queue to be scheduled on the
    event loop.

    Calls `register_async_logger` with the provided `logger` instance
    if no queue is registered for this logger in the running event loop.
    This means the implicitly created queue will have the default queue size.

    All arguments are passed to the sync `warning` function as is.
    """

    await _async_log_event(_warning, logger, msg, details, err)


async def async_error(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Enqueue an asynchronous error logging event.

    This function registers a future call to `error` to the async queue to be scheduled on the
    event loop.

    Calls `register_async_logger` with the provided `logger` instance
    if no queue is registered for this logger in the running event loop.
    This means the implicitly created queue will have the default queue size.

    All arguments are passed to the sync `error` function as is.
    """

    await _async_log_event(_error, logger, msg, details, err)


async def async_critical(
    logger: logging.Logger,
    msg: str,
    details: dict[str, Any] = {},
    *,
    err: BaseException | None = None,
) -> None:
    """Enqueue an asynchronous critical logging event.

    This function registers a future call to `critical` to the async queue to be scheduled on the
    event loop.

    Calls `register_async_logger` with the provided `logger` instance
    if no queue is registered for this logger in the running event loop.
    This means the implicitly created queue will have the default queue size.

    All arguments are passed to the sync `critical` function as is.
    """

    await _async_log_event(_critical, logger, msg, details, err)
