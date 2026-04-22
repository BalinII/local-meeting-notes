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


class FakeLlmClient:
    def check(self) -> dict[str, object]:
        return {
            "status": "ok",
            "base_url": "http://127.0.0.1:11434",
            "model_name": "llama3.1:8b",
            "models": [{"name": "llama3.1:8b"}],
        }

    def generate_json(self, prompt: str) -> dict[str, object]:
        if '"summaries": [' in prompt:
            return {
                "summaries": [
                    {
                        "title": "Executive Summary",
                        "summary_type": "executive",
                        "content": "The team agreed to ship a local-first MVP.",
                        "evidence_snippet": "Decision: we agreed to ship a local-first MVP.",
                    },
                    {
                        "title": "Detailed Summary",
                        "summary_type": "detailed",
                        "content": "The meeting covered the MVP decision, a rollout checklist, and an ownership gap.",
                        "evidence_snippet": "Action item: please write the rollout checklist.",
                    },
                ]
            }
        return {
            "actions": [
                {
                    "description": "Write the rollout checklist.",
                    "owner_name": "Unconfirmed speaker",
                    "evidence_snippet": "Action item: please write the rollout checklist.",
                    "start_offset_seconds": 1,
                    "end_offset_seconds": 2,
                }
            ],
            "decisions": [
                {
                    "description": "Ship a local-first MVP.",
                    "evidence_snippet": "Decision: we agreed to ship a local-first MVP.",
                    "start_offset_seconds": 0,
                    "end_offset_seconds": 1,
                }
            ],
            "follow_ups": [
                {
                    "description": "Clarify who owns validation.",
                    "follow_up_type": "open_question",
                    "owner_name": "Unconfirmed speaker",
                    "evidence_snippet": "Open question: who owns validation?",
                    "start_offset_seconds": 1,
                    "end_offset_seconds": 2,
                }
            ],
        }


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
    os.environ["LOCAL_LLM_BASE_URL"] = "http://127.0.0.1:11434"
    os.environ["LOCAL_LLM_MODEL"] = "llama3.1:8b"
    os.environ["LOCAL_LLM_TIMEOUT_SECONDS"] = "10"
    os.environ["LOCAL_LLM_MAX_TRANSCRIPT_CHARS"] = "8000"

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
        assert "Provider: heuristic" in rendered
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
            "LOCAL_LLM_BASE_URL",
            "LOCAL_LLM_MODEL",
            "LOCAL_LLM_TIMEOUT_SECONDS",
            "LOCAL_LLM_MAX_TRANSCRIPT_CHARS",
        ):
            os.environ.pop(key, None)


def test_cli_local_llm_provider_and_health_check(local_tmp_dir, monkeypatch) -> None:
    env_root = local_tmp_dir / "data"
    capture_id = "capture-summary-cli-llm"
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
    os.environ["LOCAL_LLM_BASE_URL"] = "http://127.0.0.1:11434"
    os.environ["LOCAL_LLM_MODEL"] = "llama3.1:8b"
    os.environ["LOCAL_LLM_TIMEOUT_SECONDS"] = "10"
    os.environ["LOCAL_LLM_MAX_TRANSCRIPT_CHARS"] = "8000"

    monkeypatch.setattr(
        "local_meeting_notes.transcription_engine.service.build_transcription_provider",
        lambda config: FakeProvider(),
    )
    monkeypatch.setattr(
        "local_meeting_notes.summarizer.providers.build_local_llm_client",
        lambda config: FakeLlmClient(),
    )
    monkeypatch.setattr(
        "local_meeting_notes.action_extractor.providers.build_local_llm_client",
        lambda config: FakeLlmClient(),
    )
    monkeypatch.setattr(
        "local_meeting_notes.app.build_local_llm_client",
        lambda config: FakeLlmClient(),
    )

    try:
        out = io.StringIO()
        with redirect_stdout(out):
            assert main(["llm", "check"]) == 0
            assert main(["transcript", "transcribe", "--capture-id", capture_id]) == 0
            assert main(["summary", "generate", "--capture-id", capture_id, "--provider", "local_llm"]) == 0
            assert main(["actions", "extract", "--capture-id", capture_id, "--provider", "local_llm"]) == 0
            assert main(["summary", "show", "--capture-id", capture_id]) == 0
            assert main(["actions", "list", "--capture-id", capture_id]) == 0

        rendered = out.getvalue()
        assert "Status: ok" in rendered
        assert "Provider: local_llm" in rendered
        assert "Model: llama3.1:8b" in rendered
        assert "Ship a local-first MVP." in rendered
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
            "LOCAL_LLM_BASE_URL",
            "LOCAL_LLM_MODEL",
            "LOCAL_LLM_TIMEOUT_SECONDS",
            "LOCAL_LLM_MAX_TRANSCRIPT_CHARS",
        ):
            os.environ.pop(key, None)
