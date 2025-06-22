# grammlog

GrammAcc's structured logging.

[Full Documentation](https://grammacc.github.io/grammlog)

Pure python package that provides structured logging to JSONL with no dependencies.

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

    cat debug.log | jq 'select(.err != null) | select(.err | contains("ValueError")) | [.msg, .traceback]'

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
