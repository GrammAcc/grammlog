import json
import os.path
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
def test_basic_logging(sync_log_func, log_level, fixt_default_logger):
    """Basic happy-path test cases."""

    assert os.path.getsize("logs/default.log") == 0

    sync_log_func(fixt_default_logger, "test message")

    log_text = Path("logs/default.log").read_text()
    print("whole test:", log_text)
    data = json.loads(log_text)

    assert data["msg"] == "test message"
