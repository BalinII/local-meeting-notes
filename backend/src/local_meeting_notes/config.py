"""Configuration helpers for the local-first backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    app_env: str
    log_level: str
    app_name: str
    audio_chunk_seconds: int
    audio_sample_rate: int
    audio_channels: int
    audio_capture_mode: str
    transcription_provider: str
    transcription_model_size: str
    transcription_device: str
    diarization_provider: str
    diarization_max_speakers: int
    summary_provider: str
    action_extraction_provider: str
    local_llm_base_url: str
    local_llm_model: str
    local_llm_timeout_seconds: int
    local_llm_max_transcript_chars: int
    data_dir: Path
    audio_output_dir: Path
    database_path: Path
    transcript_output_dir: Path
    export_output_dir: Path
    temp_output_dir: Path
    log_dir: Path
    session_state_path: Path
    audio_capture_state_path: Path
    raw_audio_retention_days: int
    delete_temp_processing_files: bool
    calendar_provider: str
    microsoft_graph_base_url: str
    microsoft_graph_access_token: str | None
    calendar_lookahead_hours: int


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(raw_value: str) -> Path:
    path = Path(raw_value)
    if path.is_absolute():
        return path
    return (project_root() / path).resolve()


def load_config(env: dict[str, str] | None = None) -> AppConfig:
    """Load environment-driven config and ensure local directories exist."""

    source = os.environ if env is None else env

    data_dir = _resolve_path(source.get("LMN_DATA_DIR", "backend/data"))
    audio_output_dir = _resolve_path(source.get("AUDIO_OUTPUT_DIR", "backend/data/audio"))
    database_path = _resolve_path(source.get("DATABASE_PATH", "backend/data/local_meeting_notes.db"))
    transcript_output_dir = _resolve_path(
        source.get("TRANSCRIPT_OUTPUT_DIR", "backend/data/transcripts")
    )
    export_output_dir = _resolve_path(source.get("EXPORT_OUTPUT_DIR", "backend/data/exports"))
    temp_output_dir = _resolve_path(source.get("TEMP_OUTPUT_DIR", "backend/data/tmp"))
    log_dir = _resolve_path(source.get("LOG_DIR", "backend/data/logs"))
    session_state_path = _resolve_path(
        source.get("SESSION_STATE_PATH", "backend/data/tmp/mock_session.json")
    )
    audio_capture_state_path = _resolve_path(
        source.get("AUDIO_CAPTURE_STATE_PATH", "backend/data/tmp/audio_capture_state.json")
    )

    for directory in (
        data_dir,
        audio_output_dir,
        transcript_output_dir,
        export_output_dir,
        temp_output_dir,
        log_dir,
        session_state_path.parent,
        audio_capture_state_path.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        app_env=source.get("APP_ENV", "development"),
        log_level=source.get("LOG_LEVEL", "INFO").upper(),
        app_name=source.get("APP_NAME", "Local Meeting Notes"),
        audio_chunk_seconds=int(source.get("AUDIO_CHUNK_SECONDS", "30")),
        audio_sample_rate=int(source.get("AUDIO_SAMPLE_RATE", "16000")),
        audio_channels=int(source.get("AUDIO_CHANNELS", "1")),
        audio_capture_mode=source.get("AUDIO_CAPTURE_MODE", "windows-loopback+microphone"),
        transcription_provider=source.get("TRANSCRIPTION_PROVIDER", "faster-whisper"),
        transcription_model_size=source.get("TRANSCRIPTION_MODEL_SIZE", "tiny"),
        transcription_device=source.get("TRANSCRIPTION_DEVICE", "cpu"),
        diarization_provider=source.get("DIARIZATION_PROVIDER", "librosa-clustering"),
        diarization_max_speakers=int(source.get("DIARIZATION_MAX_SPEAKERS", "3")),
        summary_provider=source.get("SUMMARY_PROVIDER", "heuristic"),
        action_extraction_provider=source.get("ACTION_EXTRACTION_PROVIDER", "heuristic"),
        local_llm_base_url=source.get("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434"),
        local_llm_model=source.get("LOCAL_LLM_MODEL", "llama3.1:8b"),
        local_llm_timeout_seconds=int(source.get("LOCAL_LLM_TIMEOUT_SECONDS", "45")),
        local_llm_max_transcript_chars=int(source.get("LOCAL_LLM_MAX_TRANSCRIPT_CHARS", "12000")),
        data_dir=data_dir,
        audio_output_dir=audio_output_dir,
        database_path=database_path,
        transcript_output_dir=transcript_output_dir,
        export_output_dir=export_output_dir,
        temp_output_dir=temp_output_dir,
        log_dir=log_dir,
        session_state_path=session_state_path,
        audio_capture_state_path=audio_capture_state_path,
        raw_audio_retention_days=int(source.get("RAW_AUDIO_RETENTION_DAYS", "14")),
        delete_temp_processing_files=source.get("DELETE_TEMP_PROCESSING_FILES", "1") not in {"0", "false", "False"},
        calendar_provider=source.get("CALENDAR_PROVIDER", "none"),
        microsoft_graph_base_url=source.get("MICROSOFT_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0"),
        microsoft_graph_access_token=source.get("MICROSOFT_GRAPH_ACCESS_TOKEN"),
        calendar_lookahead_hours=int(source.get("CALENDAR_LOOKAHEAD_HOURS", "48")),
    )
