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
    assert config.database_path == local_tmp_dir / "data" / "app.db"
    assert config.audio_output_dir.exists()
    assert config.log_dir.exists()
    assert config.session_state_path.parent.exists()
