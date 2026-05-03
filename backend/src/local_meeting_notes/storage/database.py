"""SQLite connection and bootstrap helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..config import AppConfig
from .schema import SCHEMA_STATEMENTS


MEETING_MIGRATIONS = {
    "capture_id": "ALTER TABLE meetings ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "created_at": "ALTER TABLE meetings ADD COLUMN created_at TEXT",
    "updated_at": "ALTER TABLE meetings ADD COLUMN updated_at TEXT",
    "manual_title": "ALTER TABLE meetings ADD COLUMN manual_title INTEGER NOT NULL DEFAULT 1",
    "recorded_seconds": "ALTER TABLE meetings ADD COLUMN recorded_seconds INTEGER NOT NULL DEFAULT 0",
    "last_recording_started_at": "ALTER TABLE meetings ADD COLUMN last_recording_started_at TEXT",
    "reviewed_at": "ALTER TABLE meetings ADD COLUMN reviewed_at TEXT",
    "exported_at": "ALTER TABLE meetings ADD COLUMN exported_at TEXT",
    "archived_at": "ALTER TABLE meetings ADD COLUMN archived_at TEXT",
    "last_processed_at": "ALTER TABLE meetings ADD COLUMN last_processed_at TEXT",
    "last_error": "ALTER TABLE meetings ADD COLUMN last_error TEXT",
    "keep_source_audio": "ALTER TABLE meetings ADD COLUMN keep_source_audio INTEGER NOT NULL DEFAULT 1",
    "source_audio_deleted_at": "ALTER TABLE meetings ADD COLUMN source_audio_deleted_at TEXT",
    "raw_audio_expires_at": "ALTER TABLE meetings ADD COLUMN raw_audio_expires_at TEXT",
    "latest_provider_name": "ALTER TABLE meetings ADD COLUMN latest_provider_name TEXT",
    "latest_model_name": "ALTER TABLE meetings ADD COLUMN latest_model_name TEXT",
    "has_reviewed_items": "ALTER TABLE meetings ADD COLUMN has_reviewed_items INTEGER NOT NULL DEFAULT 0",
    "session_type": "ALTER TABLE meetings ADD COLUMN session_type TEXT NOT NULL DEFAULT 'ad_hoc'",
    "planned_start_at": "ALTER TABLE meetings ADD COLUMN planned_start_at TEXT",
    "planning_notes": "ALTER TABLE meetings ADD COLUMN planning_notes TEXT",
}

TRANSCRIPT_SEGMENT_MIGRATIONS = {
    "capture_id": "ALTER TABLE transcript_segments ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "source_chunk_path": "ALTER TABLE transcript_segments ADD COLUMN source_chunk_path TEXT NOT NULL DEFAULT ''",
    "transcription_status": "ALTER TABLE transcript_segments ADD COLUMN transcription_status TEXT NOT NULL DEFAULT 'pending'",
    "provider_name": "ALTER TABLE transcript_segments ADD COLUMN provider_name TEXT NOT NULL DEFAULT 'mock'",
    "model_name": "ALTER TABLE transcript_segments ADD COLUMN model_name TEXT NOT NULL DEFAULT 'mock'",
    "error_message": "ALTER TABLE transcript_segments ADD COLUMN error_message TEXT",
}

DIARIZATION_SEGMENT_MIGRATIONS = {
    "capture_id": "ALTER TABLE diarization_segments ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "source_audio_path": "ALTER TABLE diarization_segments ADD COLUMN source_audio_path TEXT NOT NULL DEFAULT ''",
    "diarization_status": "ALTER TABLE diarization_segments ADD COLUMN diarization_status TEXT NOT NULL DEFAULT 'pending'",
    "provider_name": "ALTER TABLE diarization_segments ADD COLUMN provider_name TEXT NOT NULL DEFAULT 'mock'",
    "confidence": "ALTER TABLE diarization_segments ADD COLUMN confidence REAL",
    "error_message": "ALTER TABLE diarization_segments ADD COLUMN error_message TEXT",
}

SUMMARY_MIGRATIONS = {
    "capture_id": "ALTER TABLE summaries ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "title": "ALTER TABLE summaries ADD COLUMN title TEXT NOT NULL DEFAULT ''",
    "evidence_snippet": "ALTER TABLE summaries ADD COLUMN evidence_snippet TEXT",
    "provider_name": "ALTER TABLE summaries ADD COLUMN provider_name TEXT NOT NULL DEFAULT 'heuristic'",
    "model_name": "ALTER TABLE summaries ADD COLUMN model_name TEXT",
    "generated_at": "ALTER TABLE summaries ADD COLUMN generated_at TEXT",
    "review_status": "ALTER TABLE summaries ADD COLUMN review_status TEXT NOT NULL DEFAULT 'generated'",
    "reviewed_description": "ALTER TABLE summaries ADD COLUMN reviewed_description TEXT",
    "reviewed_owner_name": "ALTER TABLE summaries ADD COLUMN reviewed_owner_name TEXT",
    "reviewed_at": "ALTER TABLE summaries ADD COLUMN reviewed_at TEXT",
}

ACTION_MIGRATIONS = {
    "capture_id": "ALTER TABLE actions ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "evidence_snippet": "ALTER TABLE actions ADD COLUMN evidence_snippet TEXT",
    "start_offset_seconds": "ALTER TABLE actions ADD COLUMN start_offset_seconds INTEGER",
    "end_offset_seconds": "ALTER TABLE actions ADD COLUMN end_offset_seconds INTEGER",
    "provider_name": "ALTER TABLE actions ADD COLUMN provider_name TEXT NOT NULL DEFAULT 'heuristic'",
    "model_name": "ALTER TABLE actions ADD COLUMN model_name TEXT",
    "generated_at": "ALTER TABLE actions ADD COLUMN generated_at TEXT",
    "review_status": "ALTER TABLE actions ADD COLUMN review_status TEXT NOT NULL DEFAULT 'generated'",
    "reviewed_description": "ALTER TABLE actions ADD COLUMN reviewed_description TEXT",
    "reviewed_owner_name": "ALTER TABLE actions ADD COLUMN reviewed_owner_name TEXT",
    "reviewed_at": "ALTER TABLE actions ADD COLUMN reviewed_at TEXT",
}

DECISION_MIGRATIONS = {
    "capture_id": "ALTER TABLE decisions ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "evidence_snippet": "ALTER TABLE decisions ADD COLUMN evidence_snippet TEXT",
    "start_offset_seconds": "ALTER TABLE decisions ADD COLUMN start_offset_seconds INTEGER",
    "end_offset_seconds": "ALTER TABLE decisions ADD COLUMN end_offset_seconds INTEGER",
    "provider_name": "ALTER TABLE decisions ADD COLUMN provider_name TEXT NOT NULL DEFAULT 'heuristic'",
    "model_name": "ALTER TABLE decisions ADD COLUMN model_name TEXT",
    "generated_at": "ALTER TABLE decisions ADD COLUMN generated_at TEXT",
    "review_status": "ALTER TABLE decisions ADD COLUMN review_status TEXT NOT NULL DEFAULT 'generated'",
    "reviewed_description": "ALTER TABLE decisions ADD COLUMN reviewed_description TEXT",
    "reviewed_owner_name": "ALTER TABLE decisions ADD COLUMN reviewed_owner_name TEXT",
    "reviewed_at": "ALTER TABLE decisions ADD COLUMN reviewed_at TEXT",
}

FOLLOW_UP_MIGRATIONS = {
    "capture_id": "ALTER TABLE follow_ups ADD COLUMN capture_id TEXT NOT NULL DEFAULT ''",
    "follow_up_type": "ALTER TABLE follow_ups ADD COLUMN follow_up_type TEXT NOT NULL DEFAULT 'follow_up'",
    "owner_name": "ALTER TABLE follow_ups ADD COLUMN owner_name TEXT",
    "status": "ALTER TABLE follow_ups ADD COLUMN status TEXT NOT NULL DEFAULT 'open'",
    "evidence_snippet": "ALTER TABLE follow_ups ADD COLUMN evidence_snippet TEXT",
    "start_offset_seconds": "ALTER TABLE follow_ups ADD COLUMN start_offset_seconds INTEGER",
    "end_offset_seconds": "ALTER TABLE follow_ups ADD COLUMN end_offset_seconds INTEGER",
    "provider_name": "ALTER TABLE follow_ups ADD COLUMN provider_name TEXT NOT NULL DEFAULT 'heuristic'",
    "model_name": "ALTER TABLE follow_ups ADD COLUMN model_name TEXT",
    "generated_at": "ALTER TABLE follow_ups ADD COLUMN generated_at TEXT",
    "review_status": "ALTER TABLE follow_ups ADD COLUMN review_status TEXT NOT NULL DEFAULT 'generated'",
    "reviewed_description": "ALTER TABLE follow_ups ADD COLUMN reviewed_description TEXT",
    "reviewed_owner_name": "ALTER TABLE follow_ups ADD COLUMN reviewed_owner_name TEXT",
    "reviewed_at": "ALTER TABLE follow_ups ADD COLUMN reviewed_at TEXT",
}


def create_connection(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection_context(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = create_connection(database_path)
    try:
        yield connection
    finally:
        connection.close()


def bootstrap_database(config: AppConfig) -> None:
    with connection_context(config.database_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        _apply_schema_migrations(connection)
        connection.commit()


def _apply_schema_migrations(connection: sqlite3.Connection) -> None:
    table_names = {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    _apply_table_migrations(connection, "meetings", MEETING_MIGRATIONS)
    transcript_columns = set()
    if "transcript_segments" in table_names:
        transcript_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(transcript_segments)").fetchall()
        }
    for column_name, statement in TRANSCRIPT_SEGMENT_MIGRATIONS.items():
        if column_name not in transcript_columns:
            connection.execute(statement)

    diarization_columns = set()
    if "diarization_segments" in table_names:
        diarization_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(diarization_segments)").fetchall()
        }
    for column_name, statement in DIARIZATION_SEGMENT_MIGRATIONS.items():
        if column_name not in diarization_columns:
            connection.execute(statement)

    _apply_table_migrations(connection, "summaries", SUMMARY_MIGRATIONS)
    _apply_table_migrations(connection, "actions", ACTION_MIGRATIONS)
    _apply_table_migrations(connection, "decisions", DECISION_MIGRATIONS)
    _apply_table_migrations(connection, "follow_ups", FOLLOW_UP_MIGRATIONS)


def _apply_table_migrations(
    connection: sqlite3.Connection, table_name: str, migrations: dict[str, str]
) -> None:
    table_names = {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    if table_name not in table_names:
        return
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for column_name, statement in migrations.items():
        if column_name not in columns:
            connection.execute(statement)
