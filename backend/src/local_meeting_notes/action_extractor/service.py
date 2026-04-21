"""Placeholder action extraction service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class ActionExtractorService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="action_extractor",
            message="Reserved for extracting actions, owners, and follow-ups from transcripts.",
        )
