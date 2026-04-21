"""SQLite and local file storage service."""

from __future__ import annotations

import logging

from ..config import AppConfig
from .database import bootstrap_database


class StorageService:
    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.storage")

    def bootstrap(self) -> None:
        bootstrap_database(self.config)
        self.logger.info("SQLite bootstrap complete at %s", self.config.database_path)

    def status(self) -> dict[str, str]:
        return {
            "component": "storage",
            "status": "ready",
            "message": "SQLite bootstrap and local artifact persistence are available.",
        }
