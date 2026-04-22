"""Minimal repository helpers for mock session persistence."""

from __future__ import annotations

import sqlite3

from ..models import (
    ActionRecord,
    DiarizationSegmentRecord,
    DecisionRecord,
    FollowUpRecord,
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
            capture_id,
            source_chunk_path,
            transcription_status,
            speaker_label,
            content,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            error_message,
            is_mock
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            segment.meeting_id,
            segment.capture_id,
            segment.source_chunk_path,
            segment.transcription_status,
            segment.speaker_label,
            segment.content,
            segment.start_offset_seconds,
            segment.end_offset_seconds,
            segment.provider_name,
            segment.model_name,
            segment.error_message,
            int(segment.is_mock),
        ),
    )
    return int(cursor.lastrowid)


def insert_summary(connection: sqlite3.Connection, summary: SummaryRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO summaries (
            meeting_id,
            capture_id,
            title,
            content,
            summary_type,
            evidence_snippet,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            summary.meeting_id,
            summary.capture_id,
            summary.title,
            summary.content,
            summary.summary_type,
            summary.evidence_snippet,
            summary.provider_name,
            summary.model_name,
            summary.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_action(connection: sqlite3.Connection, action: ActionRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO actions (
            meeting_id,
            capture_id,
            description,
            owner_name,
            status,
            evidence_snippet,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action.meeting_id,
            action.capture_id,
            action.description,
            action.owner_name,
            action.status,
            action.evidence_snippet,
            action.start_offset_seconds,
            action.end_offset_seconds,
            action.provider_name,
            action.model_name,
            action.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_decision(connection: sqlite3.Connection, decision: DecisionRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO decisions (
            meeting_id,
            description,
            capture_id,
            evidence_snippet,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision.meeting_id,
            decision.description,
            decision.capture_id,
            decision.evidence_snippet,
            decision.start_offset_seconds,
            decision.end_offset_seconds,
            decision.provider_name,
            decision.model_name,
            decision.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_follow_up(connection: sqlite3.Connection, follow_up: FollowUpRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO follow_ups (
            meeting_id,
            capture_id,
            description,
            follow_up_type,
            owner_name,
            status,
            evidence_snippet,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            follow_up.meeting_id,
            follow_up.capture_id,
            follow_up.description,
            follow_up.follow_up_type,
            follow_up.owner_name,
            follow_up.status,
            follow_up.evidence_snippet,
            follow_up.start_offset_seconds,
            follow_up.end_offset_seconds,
            follow_up.provider_name,
            follow_up.model_name,
            follow_up.generated_at,
        ),
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


def ensure_meeting_for_capture(connection: sqlite3.Connection, capture_id: str) -> int:
    external_id = f"capture:{capture_id}"
    row = connection.execute(
        "SELECT id FROM meetings WHERE external_id = ?",
        (external_id,),
    ).fetchone()
    if row is not None:
        return int(row["id"])

    return insert_meeting(
        connection,
        MeetingRecord(
            id=None,
            external_id=external_id,
            title=f"Audio Capture {capture_id}",
            status="transcription_pending",
            started_at="1970-01-01T00:00:00+00:00",
        ),
    )


def delete_transcript_segments_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM transcript_segments WHERE capture_id = ?", (capture_id,))


def fetch_transcript_segments_for_capture(
    connection: sqlite3.Connection, capture_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM transcript_segments
        WHERE capture_id = ?
        ORDER BY start_offset_seconds, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_transcription_status(connection: sqlite3.Connection, capture_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            capture_id,
            COUNT(*) AS total_segments,
            SUM(CASE WHEN transcription_status = 'completed' THEN 1 ELSE 0 END) AS completed_segments,
            SUM(CASE WHEN transcription_status = 'failed' THEN 1 ELSE 0 END) AS failed_segments,
            SUM(CASE WHEN transcription_status = 'pending' THEN 1 ELSE 0 END) AS pending_segments
        FROM transcript_segments
        WHERE capture_id = ?
        GROUP BY capture_id
        """,
        (capture_id,),
    ).fetchone()


def delete_summaries_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM summaries WHERE capture_id = ?", (capture_id,))


def delete_actions_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM actions WHERE capture_id = ?", (capture_id,))


def delete_decisions_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM decisions WHERE capture_id = ?", (capture_id,))


def delete_follow_ups_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM follow_ups WHERE capture_id = ?", (capture_id,))


def fetch_summaries_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM summaries
        WHERE capture_id = ?
        ORDER BY summary_type, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_actions_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM actions
        WHERE capture_id = ?
        ORDER BY id
        """,
        (capture_id,),
    ).fetchall()


def fetch_decisions_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM decisions
        WHERE capture_id = ?
        ORDER BY id
        """,
        (capture_id,),
    ).fetchall()


def fetch_follow_ups_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM follow_ups
        WHERE capture_id = ?
        ORDER BY follow_up_type, id
        """,
        (capture_id,),
    ).fetchall()


def insert_diarization_segment(
    connection: sqlite3.Connection, segment: DiarizationSegmentRecord
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO diarization_segments (
            meeting_id,
            capture_id,
            source_audio_path,
            diarization_status,
            speaker_label,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            confidence,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            segment.meeting_id,
            segment.capture_id,
            segment.source_audio_path,
            segment.diarization_status,
            segment.speaker_label,
            segment.start_offset_seconds,
            segment.end_offset_seconds,
            segment.provider_name,
            segment.confidence,
            segment.error_message,
        ),
    )
    return int(cursor.lastrowid)


def delete_diarization_segments_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM diarization_segments WHERE capture_id = ?", (capture_id,))


def fetch_diarization_segments_for_capture(
    connection: sqlite3.Connection, capture_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM diarization_segments
        WHERE capture_id = ?
        ORDER BY start_offset_seconds, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_diarization_status(connection: sqlite3.Connection, capture_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            capture_id,
            COUNT(*) AS total_segments,
            SUM(CASE WHEN diarization_status = 'completed' THEN 1 ELSE 0 END) AS completed_segments,
            SUM(CASE WHEN diarization_status = 'failed' THEN 1 ELSE 0 END) AS failed_segments,
            SUM(CASE WHEN diarization_status = 'pending' THEN 1 ELSE 0 END) AS pending_segments
        FROM diarization_segments
        WHERE capture_id = ?
        GROUP BY capture_id
        """,
        (capture_id,),
    ).fetchone()


def apply_speaker_labels_to_transcript_segments(
    connection: sqlite3.Connection, capture_id: str
) -> None:
    transcript_rows = fetch_transcript_segments_for_capture(connection, capture_id)
    diarization_rows = fetch_diarization_segments_for_capture(connection, capture_id)
    for transcript in transcript_rows:
        best_label = "Unknown"
        best_overlap_ratio = 0.0
        best_midpoint_distance = None
        transcript_duration = max(
            0.5, transcript["end_offset_seconds"] - transcript["start_offset_seconds"]
        )
        transcript_midpoint = (
            transcript["start_offset_seconds"] + transcript["end_offset_seconds"]
        ) / 2
        for diarization in diarization_rows:
            if diarization["diarization_status"] != "completed":
                continue
            overlap = min(
                transcript["end_offset_seconds"], diarization["end_offset_seconds"]
            ) - max(transcript["start_offset_seconds"], diarization["start_offset_seconds"])
            if overlap > 0:
                overlap_ratio = overlap / transcript_duration
                if overlap_ratio > best_overlap_ratio:
                    best_overlap_ratio = overlap_ratio
                    best_label = diarization["speaker_label"]
                    best_midpoint_distance = 0.0
                continue

            diarization_midpoint = (
                diarization["start_offset_seconds"] + diarization["end_offset_seconds"]
            ) / 2
            midpoint_distance = abs(diarization_midpoint - transcript_midpoint)
            if best_overlap_ratio == 0 and (
                best_midpoint_distance is None or midpoint_distance < best_midpoint_distance
            ):
                best_midpoint_distance = midpoint_distance
                best_label = diarization["speaker_label"]

        if best_overlap_ratio < 0.2 and (best_midpoint_distance is None or best_midpoint_distance > 2.0):
            best_label = "Unknown"
        connection.execute(
            "UPDATE transcript_segments SET speaker_label = ? WHERE id = ?",
            (best_label, transcript["id"]),
        )
