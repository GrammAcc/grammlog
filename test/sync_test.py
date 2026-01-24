import json
from pathlib import Path

import pytest

import grammlog

cases = [
    (grammlog.debug, grammlog.Level.DEBUG),
    (grammlog.info, grammlog.Level.INFO),
    (grammlog.warning, grammlog.Level.WARNING),
    (grammlog.error, grammlog.Level.ERROR),
    (grammlog.critical, grammlog.Level.CRITICAL),
]


@pytest.mark.parametrize("sync_log_func,log_level", cases)
def test_basic_logging(sync_log_func, log_level, fixt_random_logger):
    """Basic happy-path test cases."""

    new_logger, rand_name = fixt_random_logger()

    sync_log_func(new_logger, "test message")

    log_text = Path(f"logs/{rand_name}.log").read_text()
    data = json.loads(log_text)

    assert data["msg"] == "test message"
