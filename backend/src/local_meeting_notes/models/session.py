"""Session models used by the mock CLI lifecycle."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MeetingSession:
    """Represents a local mock meeting session."""

    meeting_id: str
    title: str
    workspace_dir: Path
    status: str = "active"
    participants: list[str] = field(default_factory=list)
