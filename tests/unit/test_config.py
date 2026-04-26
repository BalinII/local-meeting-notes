from local_meeting_notes.config import load_config


def test_load_config_resolves_and_creates_directories(local_tmp_dir) -> None:
    env = {
        "APP_ENV": "test",
        "LOG_LEVEL": "debug",
        "LMN_DATA_DIR": str(local_tmp_dir / "data"),
        "AUDIO_OUTPUT_DIR": str(local_tmp_dir / "data" / "audio"),
        "DATABASE_PATH": str(local_tmp_dir / "data" / "app.db"),
        "TRANSCRIPT_OUTPUT_DIR": str(local_tmp_dir / "data" / "transcripts"),
        "EXPORT_OUTPUT_DIR": str(local_tmp_dir / "data" / "exports"),
        "TEMP_OUTPUT_DIR": str(local_tmp_dir / "data" / "tmp"),
        "LOG_DIR": str(local_tmp_dir / "data" / "logs"),
        "SESSION_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "session.json"),
        "AUDIO_CAPTURE_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "audio_capture_state.json"),
        "TRANSCRIPTION_PROVIDER": "faster-whisper",
        "TRANSCRIPTION_MODEL_SIZE": "tiny",
        "TRANSCRIPTION_DEVICE": "cpu",
        "DIARIZATION_PROVIDER": "librosa-clustering",
        "DIARIZATION_MAX_SPEAKERS": "3",
        "SUMMARY_PROVIDER": "local_llm",
        "ACTION_EXTRACTION_PROVIDER": "heuristic",
        "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11434",
        "LOCAL_LLM_MODEL": "llama3.1:8b",
        "LOCAL_LLM_TIMEOUT_SECONDS": "25",
        "LOCAL_LLM_MAX_TRANSCRIPT_CHARS": "8000",
        "RAW_AUDIO_RETENTION_DAYS": "21",
        "DELETE_TEMP_PROCESSING_FILES": "0",
    }

    config = load_config(env=env)

    assert config.app_env == "test"
    assert config.log_level == "DEBUG"
    assert config.audio_chunk_seconds == 30
    assert config.audio_sample_rate == 16000
    assert config.audio_channels == 1
    assert config.transcription_provider == "faster-whisper"
    assert config.transcription_model_size == "tiny"
    assert config.transcription_device == "cpu"
    assert config.diarization_provider == "librosa-clustering"
    assert config.diarization_max_speakers == 3
    assert config.summary_provider == "local_llm"
    assert config.action_extraction_provider == "heuristic"
    assert config.local_llm_base_url == "http://127.0.0.1:11434"
    assert config.local_llm_model == "llama3.1:8b"
    assert config.local_llm_timeout_seconds == 25
    assert config.local_llm_max_transcript_chars == 8000
    assert config.raw_audio_retention_days == 21
    assert config.delete_temp_processing_files is False
    assert config.database_path == local_tmp_dir / "data" / "app.db"
    assert config.audio_output_dir.exists()
    assert config.log_dir.exists()
    assert config.session_state_path.parent.exists()
