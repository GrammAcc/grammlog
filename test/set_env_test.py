import os

import grammlog


def test_set_env():
    grammlog.set_env(
        default_grammlog_level=grammlog.Level.ERROR,
        grammlog_level=grammlog.Level.DEBUG,
        default_grammlog_dir="logs/set_env_default",
        grammlog_dir="logs/set_env",
    )
    assert os.getenv("GRAMMLOG_DIR") == "logs/set_env"
    assert os.getenv("DEFAULT_GRAMMLOG_DIR") == "logs/set_env_default"
    assert os.getenv("DEFAULT_GRAMMLOG_LEVEL") == "ERROR"
    assert os.getenv("GRAMMLOG_LEVEL") == "DEBUG"
