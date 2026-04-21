"""Helpers for consistent placeholder responses."""

from dataclasses import dataclass


@dataclass(slots=True)
class PlaceholderStatus:
    component: str
    status: str = "stub"
    message: str = "Not implemented in Phase 1."
