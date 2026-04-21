"""Base record models backed by the Phase 2 SQLite schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MeetingRecord:
    id: int | None
    external_id: str
    title: str
    status: str
    started_at: str
    ended_at: str | None = None


@dataclass(slots=True)
class ParticipantRecord:
    id: int | None
    meeting_id: int
    display_name: str
    source: str = "mock"


@dataclass(slots=True)
class TranscriptSegmentRecord:
    id: int | None
    meeting_id: int
    speaker_label: str
    content: str
    start_offset_seconds: int
    end_offset_seconds: int
    is_mock: bool = True


@dataclass(slots=True)
class SummaryRecord:
    id: int | None
    meeting_id: int
    content: str
    summary_type: str = "mock"


@dataclass(slots=True)
class ActionRecord:
    id: int | None
    meeting_id: int
    description: str
    owner_name: str | None = None
    status: str = "open"


@dataclass(slots=True)
class DecisionRecord:
    id: int | None
    meeting_id: int
    description: str
