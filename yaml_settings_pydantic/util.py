from __future__ import annotations

import logging
from os import environ


def get_logger(name):
    logger = logging.getLogger(name)
    if environ.get("YAML_SETTINGS_PYDANTIC_LOGGER") == "true":
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    return logger
