"""Placeholder diarization engine service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class DiarizationEngineService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="diarization_engine",
            message="Reserved for speaker turn segmentation and diarization workflows.",
        )
