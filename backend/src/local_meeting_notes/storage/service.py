"""Placeholder SQLite and local file storage service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class StorageService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="storage",
            message="Reserved for SQLite schema management and local artifact persistence.",
        )
