from __future__ import annotations

import logging
from pathlib import Path

from local_meeting_notes.audio_capture.service import AudioCaptureService
from local_meeting_notes.audio_capture.worker import run_capture_worker
from local_meeting_notes.audio_capture.state import read_capture_state, write_capture_state
from local_meeting_notes.config import load_config


def _build_config(local_tmp_dir: Path):
    return load_config(
        env={
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
    )


def test_loopback_selection_uses_loopback_microphone_api(local_tmp_dir, monkeypatch) -> None:
    config = _build_config(local_tmp_dir)
    service = AudioCaptureService(config)
    calls: list[tuple[str | None, bool]] = []

    class DummySpeaker:
        id = "speaker-1"
        name = "Speakers"

    class DummySoundcard:
        @staticmethod
        def default_speaker():
            return DummySpeaker()

        @staticmethod
        def get_microphone(device_id, include_loopback=False):
            calls.append((device_id, include_loopback))
            return object()

    loopback = service._get_loopback_microphone(DummySoundcard)

    assert loopback is not None
    assert calls == [("speaker-1", True)]


def test_loopback_startup_failure_sets_failed_state(local_tmp_dir, monkeypatch) -> None:
    config = _build_config(local_tmp_dir)
    state_path = config.audio_capture_state_path
    stop_path = config.temp_output_dir / "capture-debug.stop"
    write_capture_state(
        state_path,
        {
            "capture_id": "capture-debug",
            "output_dir": str(config.audio_output_dir / "capture-debug"),
            "stop_request_path": str(stop_path),
            "chunk_seconds": 1,
            "sample_rate": 16000,
            "channels": 1,
            "include_microphone": False,
            "include_loopback": True,
            "status": "starting",
            "pid": 123,
            "chunk_files": [],
            "last_error": None,
        },
    )

    class FailingLoopback:
        name = "Loopback Speakers"
        id = "speaker-1"

        @staticmethod
        def recorder(*, samplerate, channels):
            raise RuntimeError("loopback open failed")

    class DummySpeaker:
        id = "speaker-1"
        name = "Speakers"

    class DummySoundcard:
        @staticmethod
        def default_speaker():
            return DummySpeaker()

        @staticmethod
        def get_microphone(device_id, include_loopback=False):
            return FailingLoopback()

        @staticmethod
        def default_microphone():
            raise AssertionError("microphone path should not be used")

    class DummySoundfile:
        @staticmethod
        def write(path, frames, sample_rate):
            raise AssertionError("no chunk should be written on startup failure")

    monkeypatch.setattr(
        "local_meeting_notes.audio_capture.worker.load_audio_dependencies",
        lambda: (DummySoundcard(), DummySoundfile()),
    )

    result = run_capture_worker(config, state_path)
    state = read_capture_state(state_path)

    assert result == 1
    assert state is not None
    assert state["status"] == "failed"
    assert "loopback" in state["last_error"]
