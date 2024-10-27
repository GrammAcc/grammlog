import os
import os.path
import random
import string
from pathlib import Path

import grammlog


def test_log_level_override(fixt_default_logger):
    """Ensure that the DEFAULT_GRAMMLOG_LEVEL can be overriden with the GRAMMLOG_LEVEL env var."""

    assert os.path.getsize("logs/default.log") == 0
    grammlog.debug(fixt_default_logger, "test message")
    data = Path("logs/default.log").read_text()
    assert "test message" in data
    os.environ["GRAMMLOG_LEVEL"] = "INFO"
    rand_name = "".join([random.choice(string.ascii_letters) for _ in range(8)])
    new_logger = grammlog.make_logger(rand_name)
    grammlog.debug(new_logger, "test message")
    assert os.path.getsize(f"logs/{rand_name}.log") == 0
