from __future__ import annotations

import io
import wave
from contextlib import redirect_stdout
from pathlib import Path

from local_meeting_notes.app import main
from local_meeting_notes.transcription_engine.providers import TranscriptionResult


def _write_wav(path: Path, seconds: int = 1, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * sample_rate * seconds)


class FakeProvider:
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        if "001" in chunk_path.name:
            text = "Decision: we agreed to ship a local-first MVP."
        else:
            text = "Action item: please write the rollout checklist. Open question: who owns validation?"
        return TranscriptionResult(text=text, provider_name="fake-provider", model_name="fake-model")


def test_cli_summary_and_actions_commands(local_tmp_dir, monkeypatch) -> None:
    env_root = local_tmp_dir / "data"
    capture_id = "capture-summary-cli"
    _write_wav(env_root / "audio" / capture_id / "loopback" / "loopback_001.wav")
    _write_wav(env_root / "audio" / capture_id / "loopback" / "loopback_002.wav")

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
        lambda config: FakeProvider(),
    )

    try:
        out = io.StringIO()
        with redirect_stdout(out):
            assert main(["transcript", "transcribe", "--capture-id", capture_id]) == 0
            assert main(["summary", "generate", "--capture-id", capture_id]) == 0
            assert main(["summary", "show", "--capture-id", capture_id]) == 0
            assert main(["actions", "extract", "--capture-id", capture_id]) == 0
            assert main(["actions", "list", "--capture-id", capture_id]) == 0

        rendered = out.getvalue()
        assert "Summary count: 2" in rendered
        assert "Executive Summary" in rendered
        assert "Actions:" in rendered
        assert "Decisions:" in rendered
        assert "Follow-ups:" in rendered
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
