"""Placeholder Microsoft metadata integration service."""

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


class MicrosoftIntegrationService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="microsoft_integration",
            message="Reserved for optional metadata integration only; auth is not implemented here.",
        )
