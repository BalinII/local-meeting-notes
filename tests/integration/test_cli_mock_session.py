from local_meeting_notes.app import main
from local_meeting_notes.storage.database import connection_context


def test_cli_can_start_and_stop_mock_session(local_tmp_dir) -> None:
    env_root = local_tmp_dir / "data"
    import os

    os.environ["LMN_DATA_DIR"] = str(env_root)
    os.environ["AUDIO_OUTPUT_DIR"] = str(env_root / "audio")
    os.environ["DATABASE_PATH"] = str(env_root / "local_meeting_notes.db")
    os.environ["TRANSCRIPT_OUTPUT_DIR"] = str(env_root / "transcripts")
    os.environ["EXPORT_OUTPUT_DIR"] = str(env_root / "exports")
    os.environ["TEMP_OUTPUT_DIR"] = str(env_root / "tmp")
    os.environ["LOG_DIR"] = str(env_root / "logs")
    os.environ["SESSION_STATE_PATH"] = str(env_root / "tmp" / "session.json")
    os.environ["AUDIO_CAPTURE_STATE_PATH"] = str(env_root / "tmp" / "audio_capture_state.json")

    try:
        assert main(["session", "start", "--title", "CLI Mock Meeting"]) == 0
        assert main(["session", "stop"]) == 0

        with connection_context(env_root / "local_meeting_notes.db") as connection:
            row = connection.execute(
                "SELECT status FROM meetings ORDER BY id DESC LIMIT 1"
            ).fetchone()

        assert row["status"] == "stopped"
    finally:
        for key in (
            "LMN_DATA_DIR",
            "AUDIO_OUTPUT_DIR",
            "DATABASE_PATH",
            "TRANSCRIPT_OUTPUT_DIR",
            "EXPORT_OUTPUT_DIR",
            "TEMP_OUTPUT_DIR",
            "LOG_DIR",
            "SESSION_STATE_PATH",
            "AUDIO_CAPTURE_STATE_PATH",
        ):
            os.environ.pop(key, None)
