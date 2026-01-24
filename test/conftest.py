import os
import random
import shutil
import string

import pytest

import grammlog


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree("logs")


def _reset_env_vars():
    for varname in [
        "DEFAULT_GRAMMLOG_DIR",
        "GRAMMLOG_DIR",
        "DEFAULT_GRAMMLOG_LEVEL",
        "GRAMMLOG_LEVEL",
    ]:
        if varname in os.environ:
            del os.environ[varname]


@pytest.fixture(autouse=True)
def reset_env():
    _reset_env_vars()
    yield None
    _reset_env_vars()


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    _reset_env_vars()


@pytest.fixture
def fixt_default_logger():

    logger = grammlog.make_logger("default", log_dir="logs", log_level=grammlog.Level.INFO)

    with open("logs/default.log", "w"):
        # Truncate log file.
        pass

    return logger


@pytest.fixture
def fixt_random_logger():
    def f():
        rand_name = "".join([random.choice(string.ascii_letters) for _ in range(8)])
        logger = grammlog.make_logger(rand_name, log_level=grammlog.Level.DEBUG)
        return logger, rand_name

    return f
