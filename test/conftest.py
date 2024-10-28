import os
import random
import string

import pytest

import grammlog


def _reset_env_vars():
    os.environ["GRAMMLOG_DIR"] = "logs"
    os.environ["DEFAULT_GRAMMLOG_LEVEL"] = "DEBUG"
    if "GRAMMLOG_LEVEL" in os.environ:
        del os.environ["GRAMMLOG_LEVEL"]


@pytest.fixture
def reset_env():
    _reset_env_vars()
    yield None
    _reset_env_vars()


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    _reset_env_vars()


@pytest.fixture
def fixt_default_logger():

    with open("logs/default.log", "w"):
        # Truncate log file.
        pass

    return grammlog.make_logger("default")


@pytest.fixture
def fixt_random_logger():
    def f():
        rand_name = "".join([random.choice(string.ascii_letters) for _ in range(8)])
        logger = grammlog.make_logger(rand_name)
        return logger, rand_name

    return f
