"""Logging setup and security sanitization."""

import logging
import re
import sys
from app.config import settings

# Regex to detect possible bot tokens (e.g. 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ)
TOKEN_REGEX = re.compile(r"\b\d{8,12}:[a-zA-Z0-9_-]{35}\b")
API_KEY_REGEX = re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b")


class SanitizingFilter(logging.Filter):
    """Filter that masks tokens and API keys from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = TOKEN_REGEX.sub("[REDACTED_BOT_TOKEN]", record.msg)
            record.msg = API_KEY_REGEX.sub("[REDACTED_API_KEY]", record.msg)
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    arg = TOKEN_REGEX.sub("[REDACTED_BOT_TOKEN]", arg)
                    arg = API_KEY_REGEX.sub("[REDACTED_API_KEY]", arg)
                sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True


def setup_logger(name: str = "tsa_bot") -> logging.Logger:
    """Configures and returns a sanitizing logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(SanitizingFilter())

    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logger("tsa_bot")
