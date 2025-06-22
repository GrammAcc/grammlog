import asyncio
import datetime
import json
import os.path
import time
from pathlib import Path

import pytest

import grammlog


@pytest.fixture(autouse=True)
async def reset_async_loggers():
    await grammlog.flush()
    yield None
    await grammlog.flush()


cases = [
    grammlog.async_debug,
    grammlog.async_info,
    grammlog.async_warning,
    grammlog.async_error,
    grammlog.async_critical,
]


@pytest.mark.parametrize("async_log_func", cases)
async def test_basic_async_logging(async_log_func, fixt_default_logger):
    """Basic happy-path test cases."""

    assert os.path.getsize("logs/default.log") == 0

    grammlog.register_async_logger(fixt_default_logger)

    await async_log_func(fixt_default_logger, "test message")

    await grammlog.deregister_async_logger(fixt_default_logger)

    log_text = Path("logs/default.log").read_text()
    data = json.loads(log_text)

    assert data["msg"] == "test message"


@pytest.mark.parametrize("async_log_func", cases)
async def test_async_timestamp(async_log_func, fixt_default_logger):
    """Ensure that async logging events use the timestamp for when the event is
    enqueued and not when the event is actually flushed to disk."""

    assert os.path.getsize("logs/default.log") == 0

    grammlog.register_async_logger(fixt_default_logger)

    async def log_event():
        await async_log_func(fixt_default_logger, "test message")

    async def block_loop():
        time.sleep(0.5)
        return datetime.datetime.now(datetime.timezone.utc).timestamp()

    _, later_timestamp = await asyncio.gather(log_event(), block_loop())
    await grammlog.deregister_async_logger(fixt_default_logger)

    log_text = Path("logs/default.log").read_text()
    data = json.loads(log_text)

    assert data["timestamp"] < later_timestamp - 0.4


@pytest.mark.parametrize("async_log_func", cases)
async def test_async_logging_value_error_when_logger_not_registered(
    async_log_func, fixt_default_logger
):
    """Changed in version 1.3.0
    Calling any of the `async_*` logging functions should register a
    new async queue if one is not already registered for that logger
    instead of raising an exception."""

    try:
        await async_log_func(fixt_default_logger, "some message")
    except Exception as e:
        assert False, f"Exception {e} was raised"


async def test_register_async_logger_value_error_when_already_registered(fixt_default_logger):
    """The `register_async_logger` function should raise a ValueError if the
    provided logger is already registered."""

    grammlog.register_async_logger(fixt_default_logger)
    with pytest.raises(ValueError):
        grammlog.register_async_logger(fixt_default_logger)


async def test_deregister_async_logger_value_error_when_not_registered(fixt_default_logger):
    """The `deregister_async_logger` function should raise a ValueError if the
    provided logger is NOT already registered."""

    with pytest.raises(ValueError):
        await grammlog.deregister_async_logger(fixt_default_logger)


def test_register_async_logger_runtime_error_when_no_running_loop(fixt_default_logger):
    """The `register_async_logger` function is synchronous, but it creates a background
    task, so it needs a running event loop."""

    with pytest.raises(RuntimeError, match="register_async_logger requires a running event loop"):
        grammlog.register_async_logger(fixt_default_logger)
