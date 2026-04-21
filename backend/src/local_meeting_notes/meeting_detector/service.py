"""Placeholder meeting detection for local Windows sessions."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class MeetingDetectorService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="meeting_detector",
            message="Reserved for local meeting source detection and mock session awareness.",
        )
