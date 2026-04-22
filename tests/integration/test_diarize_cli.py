from __future__ import annotations

import io
import wave
from contextlib import redirect_stdout
from pathlib import Path

from local_meeting_notes.app import main
from local_meeting_notes.diarization_engine.providers import DiarizationResultSegment
from local_meeting_notes.transcription_engine.providers import TranscriptionResult


def _write_wav(path: Path, seconds: int = 1, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * sample_rate * seconds)


class FakeTranscriptionProvider:
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        return TranscriptionResult(
            text=f"cli transcript for {chunk_path.name}",
            provider_name="fake-transcription",
            model_name="fake-model",
        )


class FakeDiarizationProvider:
    def diarize_file(self, audio_path: Path) -> list[DiarizationResultSegment]:
        return [
            DiarizationResultSegment(
                start_offset_seconds=0,
                end_offset_seconds=1,
                speaker_label="Speaker 2",
                confidence=0.6,
            )
        ]


def test_cli_diarize_commands(local_tmp_dir, monkeypatch) -> None:
    env_root = local_tmp_dir / "data"
    capture_id = "capture-diarize-cli"
    _write_wav(env_root / "audio" / capture_id / "loopback" / "loopback_001.wav")

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

    monkeypatch.setattr(
        "local_meeting_notes.transcription_engine.service.build_transcription_provider",
        lambda config: FakeTranscriptionProvider(),
    )
    monkeypatch.setattr(
        "local_meeting_notes.diarization_engine.service.build_diarization_provider",
        lambda config: FakeDiarizationProvider(),
    )

    try:
        out = io.StringIO()
        with redirect_stdout(out):
            assert main(["transcript", "transcribe", "--capture-id", capture_id]) == 0
            assert main(["diarize", "run", "--capture-id", capture_id]) == 0
            assert main(["diarize", "status", "--capture-id", capture_id]) == 0
            assert main(["diarize", "list", "--capture-id", capture_id]) == 0
            assert main(["transcript", "list", "--capture-id", capture_id]) == 0

        rendered = out.getvalue()
        assert "Completed audio files: 1" in rendered
        assert "Status: completed" in rendered
        assert "Speaker 2" in rendered
        assert "cli transcript for loopback_001.wav" in rendered
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
