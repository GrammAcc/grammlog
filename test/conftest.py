import os

import pytest

import grammlog


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["GRAMMLOG_DIR"] = "logs"
    os.environ["DEFAULT_GRAMMLOG_LEVEL"] = "INFO"
    grammlog.make_logger("default")


@pytest.fixture
def fixt_default_logger():

    with open("logs/default.log", "w"):
        # Truncate log file.
        pass

    return grammlog.make_logger("default")
