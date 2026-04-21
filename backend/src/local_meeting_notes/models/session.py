"""Shared session models used by placeholder services."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MeetingSession:
    """Represents a local meeting workspace without real capture state yet."""

    meeting_id: str
    title: str
    workspace_dir: Path
    participants: list[str] = field(default_factory=list)
