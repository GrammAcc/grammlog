import os
import os.path
from pathlib import Path

import pytest

import grammlog


@pytest.mark.usefixtures("reset_env")
def test_log_level_override(fixt_default_logger, fixt_random_logger):
    """Ensure that the DEFAULT_GRAMMLOG_LEVEL can be overriden with the GRAMMLOG_LEVEL env var."""

    assert os.path.getsize("logs/default.log") == 0
    grammlog.debug(fixt_default_logger, "test message")
    data = Path("logs/default.log").read_text()
    assert "test message" in data
    os.environ["GRAMMLOG_LEVEL"] = "INFO"
    new_logger, rand_name = fixt_random_logger()
    grammlog.debug(new_logger, "test message")
    assert os.path.getsize(f"logs/{rand_name}.log") == 0


@pytest.mark.usefixtures("reset_env")
@pytest.mark.parametrize("env_var", ["GRAMMLOG_DIR", "DEFAULT_GRAMMLOG_LEVEL"])
def test_runtime_error_missing_env_var(env_var):
    """The `make_logger` function should raise a RuntimeError if the required
    env vars are not defined and the corresponding override arguments are not provided
    to the function call."""

    del os.environ[env_var]
    with pytest.raises(RuntimeError, match="Missing env var:"):
        grammlog.make_logger("loggername")
