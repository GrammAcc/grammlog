import os
import os.path
from pathlib import Path

import grammlog


def test_log_level_override(fixt_random_logger):
    """Ensure that the DEFAULT_GRAMMLOG_LEVEL can be overriden with the GRAMMLOG_LEVEL env var."""

    default_logger = grammlog.make_logger("log_level_override_default")
    assert os.path.getsize("logs/log_level_override_default.log") == 0
    grammlog.info(default_logger, "test message")
    default_data = Path("logs/log_level_override_default.log").read_text()
    assert "test message" in default_data
    os.environ["GRAMMLOG_LEVEL"] = "ERROR"
    new_logger, rand_name = fixt_random_logger()
    new_logger = grammlog.make_logger("log_level_override")
    grammlog.info(new_logger, "test message")
    assert os.path.getsize("logs/log_level_override.log") == 0


def test_default_log_level(fixt_random_logger):
    """Ensure that the DEFAULT_GRAMMLOG_LEVEL is info if not set in the env"""

    new_logger = grammlog.make_logger("default_log_level_override")
    assert os.path.getsize("logs/default_log_level_override.log") == 0
    grammlog.debug(new_logger, "test message")
    assert os.path.getsize("logs/default_log_level_override.log") == 0
    grammlog.info(new_logger, "test message")
    data = Path("logs/default_log_level_override.log").read_text()
    assert "test message" in data


def test_default_log_dir(fixt_random_logger):
    """Ensure that the DEFAULT_GRAMMLOG_DIR is $PWD/logs if not set in the env"""

    new_logger, rand_name = fixt_random_logger()
    assert os.path.getsize(f"logs/{rand_name}.log") == 0
    grammlog.info(new_logger, "test message")
    data = Path(f"logs/{rand_name}.log").read_text()
    assert "test message" in data


def test_default_log_dir_override():
    """Ensure that the GRAMMLOG_DIR env var takes precedence over the
    DEFAULT_GRAMMLOG_DIR env var argument"""

    os.environ["DEFAULT_GRAMMLOG_DIR"] = "logs/default_override"
    os.environ["GRAMMLOG_DIR"] = "logs/override"
    new_logger = grammlog.make_logger("env_override")
    assert os.path.getsize("logs/override/env_override.log") == 0
    grammlog.info(new_logger, "test message")
    data = Path("logs/override/env_override.log").read_text()
    assert "test message" in data


def test_default_log_dir_argument_override():
    """Ensure that the GRAMMLOG_DIR env var takes precedence over the default_log_dir argument"""

    os.environ["GRAMMLOG_DIR"] = "logs/override"
    new_logger = grammlog.make_logger("arg_override", default_log_dir="logs/default_override")
    assert os.path.getsize("logs/override/arg_override.log") == 0
    grammlog.info(new_logger, "test message")
    data = Path("logs/override/arg_override.log").read_text()
    assert "test message" in data
