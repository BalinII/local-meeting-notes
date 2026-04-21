from local_meeting_notes.audio_capture.service import AudioCaptureService
from local_meeting_notes.config import load_config


def test_audio_capture_status_defaults_to_idle(local_tmp_dir) -> None:
    env = {
        "LMN_DATA_DIR": str(local_tmp_dir / "data"),
        "AUDIO_OUTPUT_DIR": str(local_tmp_dir / "data" / "audio"),
        "DATABASE_PATH": str(local_tmp_dir / "data" / "local_meeting_notes.db"),
        "TRANSCRIPT_OUTPUT_DIR": str(local_tmp_dir / "data" / "transcripts"),
        "EXPORT_OUTPUT_DIR": str(local_tmp_dir / "data" / "exports"),
        "TEMP_OUTPUT_DIR": str(local_tmp_dir / "data" / "tmp"),
        "LOG_DIR": str(local_tmp_dir / "data" / "logs"),
        "SESSION_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "session.json"),
        "AUDIO_CAPTURE_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "audio_capture_state.json"),
    }

    config = load_config(env=env)
    service = AudioCaptureService(config)

    status = service.status()

    assert status["status"] == "idle"
    assert "fragile" in status["message"]
