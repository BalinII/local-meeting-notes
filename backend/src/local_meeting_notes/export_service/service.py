"""Placeholder export service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class ExportService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="export_service",
            message="Reserved for Markdown, text, and document export workflows.",
        )
