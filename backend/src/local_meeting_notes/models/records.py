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
    session_type: str = "ad_hoc"
    source_type: str = "ad_hoc"
    planned_start_at: str | None = None
    planning_notes: str | None = None
    external_meeting_id: str | None = None
    imported_title: str | None = None
    imported_metadata_json: str | None = None
    capture_id: str = ""
    ended_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    manual_title: bool = True
    recorded_seconds: int = 0
    last_recording_started_at: str | None = None
    reviewed_at: str | None = None
    exported_at: str | None = None
    archived_at: str | None = None
    last_processed_at: str | None = None
    last_error: str | None = None
    keep_source_audio: bool = True
    source_audio_deleted_at: str | None = None
    raw_audio_expires_at: str | None = None
    latest_provider_name: str | None = None
    latest_model_name: str | None = None
    has_reviewed_items: bool = False


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
    capture_id: str
    source_chunk_path: str
    transcription_status: str
    speaker_label: str
    content: str
    start_offset_seconds: int
    end_offset_seconds: int
    provider_name: str = "mock"
    model_name: str = "mock"
    error_message: str | None = None
    is_mock: bool = True


@dataclass(slots=True)
class DiarizationSegmentRecord:
    id: int | None
    meeting_id: int
    capture_id: str
    source_audio_path: str
    diarization_status: str
    speaker_label: str
    start_offset_seconds: int
    end_offset_seconds: int
    provider_name: str = "mock"
    confidence: float | None = None
    error_message: str | None = None


@dataclass(slots=True)
class SummaryRecord:
    id: int | None
    meeting_id: int
    capture_id: str
    title: str
    content: str
    summary_type: str = "mock"
    evidence_snippet: str | None = None
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


@dataclass(slots=True)
class ActionRecord:
    id: int | None
    meeting_id: int
    capture_id: str
    description: str
    owner_name: str | None = None
    status: str = "open"
    evidence_snippet: str | None = None
    start_offset_seconds: int | None = None
    end_offset_seconds: int | None = None
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


@dataclass(slots=True)
class DecisionRecord:
    id: int | None
    meeting_id: int
    description: str
    capture_id: str
    evidence_snippet: str | None = None
    start_offset_seconds: int | None = None
    end_offset_seconds: int | None = None
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


@dataclass(slots=True)
class FollowUpRecord:
    id: int | None
    meeting_id: int
    capture_id: str
    description: str
    follow_up_type: str
    owner_name: str | None = None
    status: str = "open"
    evidence_snippet: str | None = None
    start_offset_seconds: int | None = None
    end_offset_seconds: int | None = None
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None
