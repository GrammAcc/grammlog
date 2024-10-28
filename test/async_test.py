import asyncio
import datetime
import json
import os.path
import time
from pathlib import Path

import pytest

import grammlog

cases = [
    (grammlog.async_debug, grammlog.Level.DEBUG),
    (grammlog.async_info, grammlog.Level.INFO),
    (grammlog.async_warning, grammlog.Level.WARNING),
    (grammlog.async_error, grammlog.Level.ERROR),
    (grammlog.async_critical, grammlog.Level.CRITICAL),
]


@pytest.mark.parametrize("async_log_func,log_level", cases)
async def test_basic_async_logging(async_log_func, log_level, fixt_default_logger):
    """Basic happy-path test cases."""

    assert os.path.getsize("logs/default.log") == 0

    grammlog.register_async_logger(fixt_default_logger)

    await async_log_func(fixt_default_logger, "test message")

    await grammlog.deregister_async_logger(fixt_default_logger)

    log_text = Path("logs/default.log").read_text()
    data = json.loads(log_text)

    assert data["msg"] == "test message"


@pytest.mark.parametrize("async_log_func,log_level", cases)
async def test_async_timestamp(async_log_func, log_level, fixt_default_logger):
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
