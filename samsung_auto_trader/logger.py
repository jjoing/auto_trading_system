"""Centralized logging setup: console + rotating file handler."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import PROJECT_DIR

LOG_PATH = PROJECT_DIR / "trading.log"

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once with console + rotating file handlers."""
    global _configured
    if _configured:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
