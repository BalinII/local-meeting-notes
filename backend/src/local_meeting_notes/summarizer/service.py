"""Placeholder summarizer service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class SummarizerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="summarizer",
            message="Reserved for local summary, decisions, and note generation.",
        )
