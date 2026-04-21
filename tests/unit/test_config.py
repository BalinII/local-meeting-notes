from pathlib import Path

from local_meeting_notes.config import load_config


def test_load_config_resolves_and_creates_directories(tmp_path: Path) -> None:
    env = {
        "APP_ENV": "test",
        "LOG_LEVEL": "debug",
        "LMN_DATA_DIR": str(tmp_path / "data"),
        "DATABASE_PATH": str(tmp_path / "data" / "app.db"),
        "TRANSCRIPT_OUTPUT_DIR": str(tmp_path / "data" / "transcripts"),
        "EXPORT_OUTPUT_DIR": str(tmp_path / "data" / "exports"),
        "TEMP_OUTPUT_DIR": str(tmp_path / "data" / "tmp"),
        "LOG_DIR": str(tmp_path / "data" / "logs"),
        "SESSION_STATE_PATH": str(tmp_path / "data" / "tmp" / "session.json"),
    }

    config = load_config(env=env)

    assert config.app_env == "test"
    assert config.log_level == "DEBUG"
    assert config.database_path == tmp_path / "data" / "app.db"
    assert config.log_dir.exists()
    assert config.session_state_path.parent.exists()
