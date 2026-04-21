"""Placeholder speaker attribution service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class SpeakerAttributionService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="speaker_attribution",
            message="Reserved for mapping diarized speakers to likely meeting participants.",
        )
