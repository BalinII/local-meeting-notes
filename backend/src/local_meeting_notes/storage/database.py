"""SQLite connection and bootstrap helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..config import AppConfig
from .schema import SCHEMA_STATEMENTS


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
