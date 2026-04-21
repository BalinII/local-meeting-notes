"""Configuration helpers for the local-first backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    app_env: str
    log_level: str
    data_dir: Path
    database_path: Path
    transcript_output_dir: Path
    export_output_dir: Path
    temp_output_dir: Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(raw_value: str) -> Path:
    path = Path(raw_value)
    if path.is_absolute():
        return path
    return (_project_root() / path).resolve()


def load_config() -> AppConfig:
    """Load a small set of environment-driven paths."""

    data_dir = _resolve_path(os.getenv("LMN_DATA_DIR", "backend/data"))
    database_path = _resolve_path(os.getenv("DATABASE_PATH", "backend/data/local_meeting_notes.db"))
    transcript_output_dir = _resolve_path(
        os.getenv("TRANSCRIPT_OUTPUT_DIR", "backend/data/transcripts")
    )
    export_output_dir = _resolve_path(os.getenv("EXPORT_OUTPUT_DIR", "backend/data/exports"))
    temp_output_dir = _resolve_path(os.getenv("TEMP_OUTPUT_DIR", "backend/data/tmp"))

    for directory in (data_dir, transcript_output_dir, export_output_dir, temp_output_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        data_dir=data_dir,
        database_path=database_path,
        transcript_output_dir=transcript_output_dir,
        export_output_dir=export_output_dir,
        temp_output_dir=temp_output_dir,
    )
