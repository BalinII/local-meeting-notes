"""Placeholder Windows audio capture service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class AudioCaptureService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="audio_capture",
            message="Reserved for Windows loopback and microphone capture orchestration.",
        )
