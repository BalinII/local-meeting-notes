from __future__ import annotations

from local_meeting_notes.storage.database import create_connection
from local_meeting_notes.storage.repository import (
    apply_speaker_labels_to_transcript_segments,
    insert_diarization_segment,
    insert_transcript_segment,
)
from local_meeting_notes.models import DiarizationSegmentRecord, TranscriptSegmentRecord


def test_transcript_label_propagation_prefers_overlap_and_nearby_segments(local_tmp_dir) -> None:
    connection = create_connection(local_tmp_dir / "alignment.db")
    connection.execute(
        """
        CREATE TABLE transcript_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            capture_id TEXT NOT NULL,
            source_chunk_path TEXT NOT NULL,
            transcription_status TEXT NOT NULL,
            speaker_label TEXT NOT NULL,
            content TEXT NOT NULL,
            start_offset_seconds INTEGER NOT NULL,
            end_offset_seconds INTEGER NOT NULL,
            provider_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            error_message TEXT,
            is_mock INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE diarization_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            capture_id TEXT NOT NULL,
            source_audio_path TEXT NOT NULL,
            diarization_status TEXT NOT NULL,
            speaker_label TEXT NOT NULL,
            start_offset_seconds INTEGER NOT NULL,
            end_offset_seconds INTEGER NOT NULL,
            provider_name TEXT NOT NULL,
            confidence REAL,
            error_message TEXT
        )
        """
    )

    insert_transcript_segment(
        connection,
        TranscriptSegmentRecord(
            id=None,
            meeting_id=1,
            capture_id="capture-a",
            source_chunk_path="audio/chunk.wav",
            transcription_status="completed",
            speaker_label="Unknown",
            content="hello world",
            start_offset_seconds=10,
            end_offset_seconds=12,
            provider_name="test",
            model_name="test",
            error_message=None,
            is_mock=False,
        ),
    )
    insert_diarization_segment(
        connection,
        DiarizationSegmentRecord(
            id=None,
            meeting_id=1,
            capture_id="capture-a",
            source_audio_path="audio/chunk.wav",
            diarization_status="completed",
            speaker_label="Speaker 2",
            start_offset_seconds=9,
            end_offset_seconds=13,
            provider_name="test",
            confidence=None,
            error_message=None,
        ),
    )
    insert_diarization_segment(
        connection,
        DiarizationSegmentRecord(
            id=None,
            meeting_id=1,
            capture_id="capture-a",
            source_audio_path="audio/chunk.wav",
            diarization_status="completed",
            speaker_label="Speaker 3",
            start_offset_seconds=30,
            end_offset_seconds=31,
            provider_name="test",
            confidence=None,
            error_message=None,
        ),
    )

    apply_speaker_labels_to_transcript_segments(connection, "capture-a")

    row = connection.execute(
        "SELECT speaker_label FROM transcript_segments WHERE capture_id = 'capture-a'"
    ).fetchone()
    assert row["speaker_label"] == "Speaker 2"

    connection.close()
