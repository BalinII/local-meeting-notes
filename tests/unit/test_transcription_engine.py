from __future__ import annotations

import wave
from pathlib import Path

from local_meeting_notes.config import load_config
from local_meeting_notes.transcription_engine.providers import TranscriptionResult
from local_meeting_notes.transcription_engine.service import TranscriptionEngineService


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


def _write_wav(path: Path, seconds: int = 1, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * sample_rate * seconds)


class FakeProvider:
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        if "002" in chunk_path.name:
            raise RuntimeError("synthetic chunk failure")
        return TranscriptionResult(
            text=f"transcript for {chunk_path.name}",
            provider_name="fake-provider",
            model_name="fake-model",
        )


def test_transcribe_capture_persists_completed_and_failed_segments(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    capture_dir = config.audio_output_dir / "capture-1234" / "microphone"
    _write_wav(capture_dir / "chunk_001.wav")
    _write_wav(capture_dir / "chunk_002.wav")

    service = TranscriptionEngineService(config, provider=FakeProvider())
    result = service.transcribe_capture("capture-1234")
    status = service.get_status("capture-1234")
    segments = service.list_segments("capture-1234")

    assert result["total_chunks"] == 2
    assert result["completed_chunks"] == 1
    assert result["failed_chunks"] == 1
    assert status["status"] == "failed"
    assert len(segments) == 2
    assert segments[0]["transcription_status"] == "completed"
    assert segments[1]["transcription_status"] == "failed"
