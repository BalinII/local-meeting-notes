"""Minimal repository helpers for mock session persistence."""

from __future__ import annotations

import sqlite3

from ..models import (
    ActionRecord,
    DecisionRecord,
    MeetingRecord,
    ParticipantRecord,
    SummaryRecord,
    TranscriptSegmentRecord,
)


def insert_meeting(connection: sqlite3.Connection, meeting: MeetingRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO meetings (external_id, title, status, started_at, ended_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (meeting.external_id, meeting.title, meeting.status, meeting.started_at, meeting.ended_at),
    )
    return int(cursor.lastrowid)


def insert_participant(connection: sqlite3.Connection, participant: ParticipantRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO participants (meeting_id, display_name, source)
        VALUES (?, ?, ?)
        """,
        (participant.meeting_id, participant.display_name, participant.source),
    )
    return int(cursor.lastrowid)


def insert_transcript_segment(
    connection: sqlite3.Connection, segment: TranscriptSegmentRecord
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO transcript_segments (
            meeting_id,
            speaker_label,
            content,
            start_offset_seconds,
            end_offset_seconds,
            is_mock
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            segment.meeting_id,
            segment.speaker_label,
            segment.content,
            segment.start_offset_seconds,
            segment.end_offset_seconds,
            int(segment.is_mock),
        ),
    )
    return int(cursor.lastrowid)


def insert_summary(connection: sqlite3.Connection, summary: SummaryRecord) -> int:
    cursor = connection.execute(
        "INSERT INTO summaries (meeting_id, content, summary_type) VALUES (?, ?, ?)",
        (summary.meeting_id, summary.content, summary.summary_type),
    )
    return int(cursor.lastrowid)


def insert_action(connection: sqlite3.Connection, action: ActionRecord) -> int:
    cursor = connection.execute(
        "INSERT INTO actions (meeting_id, description, owner_name, status) VALUES (?, ?, ?, ?)",
        (action.meeting_id, action.description, action.owner_name, action.status),
    )
    return int(cursor.lastrowid)


def insert_decision(connection: sqlite3.Connection, decision: DecisionRecord) -> int:
    cursor = connection.execute(
        "INSERT INTO decisions (meeting_id, description) VALUES (?, ?)",
        (decision.meeting_id, decision.description),
    )
    return int(cursor.lastrowid)


def update_meeting_status(
    connection: sqlite3.Connection, external_id: str, status: str, ended_at: str | None = None
) -> None:
    connection.execute(
        "UPDATE meetings SET status = ?, ended_at = ? WHERE external_id = ?",
        (status, ended_at, external_id),
    )


def fetch_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}
