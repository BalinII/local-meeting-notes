"""Helpers to seed mock meeting data for the CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ..models import (
    ActionRecord,
    DecisionRecord,
    MeetingRecord,
    MeetingSession,
    ParticipantRecord,
    SummaryRecord,
    TranscriptSegmentRecord,
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def build_mock_session(data_dir: Path, title: str | None = None) -> MeetingSession:
    meeting_id = f"mock-{uuid4().hex[:8]}"
    session_dir = data_dir / "meetings" / meeting_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return MeetingSession(
        meeting_id=meeting_id,
        title=title or "Mock Local Meeting",
        workspace_dir=session_dir,
        participants=["Alex", "Jordan"],
    )


def build_mock_records(session: MeetingSession) -> dict[str, object]:
    started_at = utc_now()
    meeting = MeetingRecord(
        id=None,
        external_id=session.meeting_id,
        title=session.title,
        status="active",
        started_at=started_at,
    )
    participants = [
        ParticipantRecord(id=None, meeting_id=0, display_name=name) for name in session.participants
    ]
    segments = [
        TranscriptSegmentRecord(
            id=None,
            meeting_id=0,
            speaker_label="Speaker 1",
            content="This is a mocked transcript segment for the backend skeleton.",
            start_offset_seconds=0,
            end_offset_seconds=12,
        ),
        TranscriptSegmentRecord(
            id=None,
            meeting_id=0,
            speaker_label="Speaker 2",
            content="Action item: prepare the Phase 3 implementation plan.",
            start_offset_seconds=13,
            end_offset_seconds=26,
        ),
    ]
    summary = SummaryRecord(
        id=None,
        meeting_id=0,
        content="Mock summary: alignment on backend skeleton and next implementation steps.",
    )
    action = ActionRecord(
        id=None,
        meeting_id=0,
        description="Prepare Phase 3 implementation plan.",
        owner_name="Jordan",
    )
    decision = DecisionRecord(
        id=None,
        meeting_id=0,
        description="Keep the solution local-first and Windows-oriented.",
    )
    return {
        "meeting": meeting,
        "participants": participants,
        "segments": segments,
        "summary": summary,
        "action": action,
        "decision": decision,
    }
