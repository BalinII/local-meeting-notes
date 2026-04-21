"""Logging setup for the backend skeleton."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import AppConfig


def configure_logging(config: AppConfig) -> logging.Logger:
    """Configure a console logger plus a local file logger."""

    logger = logging.getLogger("local_meeting_notes")
    logger.setLevel(getattr(logging, config.log_level, logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(Path(config.log_dir) / "local_meeting_notes.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
