from __future__ import annotations

import wave
from pathlib import Path

from local_meeting_notes.action_extractor.service import ActionExtractorService
from local_meeting_notes.config import load_config
from local_meeting_notes.local_llm import LocalLlmClientError
from local_meeting_notes.summarizer.service import SummarizerService
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
            "SUMMARY_PROVIDER": "local_llm",
            "ACTION_EXTRACTION_PROVIDER": "local_llm",
            "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11434",
            "LOCAL_LLM_MODEL": "llama3.1:8b",
            "LOCAL_LLM_TIMEOUT_SECONDS": "10",
            "LOCAL_LLM_MAX_TRANSCRIPT_CHARS": "8000",
        }
    )


class FakeTranscriptProvider:
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        return TranscriptionResult(
            text=(
                "Decision: we will keep the release local-first. "
                "Action item: Speaker 1 will prepare the rollout checklist. "
                "Open question: do we need extra validation for the blocker risk?"
            ),
            provider_name="fake",
            model_name="fake",
        )


class FakeLlmClient:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def generate_json(self, prompt: str) -> dict[str, object]:
        assert "Return JSON only." in prompt
        return self.payload


class FailingLlmClient:
    def generate_json(self, prompt: str) -> dict[str, object]:
        del prompt
        raise LocalLlmClientError("timed out")


def _seed_transcript(config) -> None:
    capture_dir = config.audio_output_dir / "capture-llm" / "microphone"
    capture_dir.mkdir(parents=True, exist_ok=True)
    sample = capture_dir / "chunk_001.wav"
    with wave.open(str(sample), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000)
    transcription = TranscriptionEngineService(config, provider=FakeTranscriptProvider())
    transcription.transcribe_capture("capture-llm")


def test_local_llm_summary_and_extraction_persist_metadata(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_transcript(config)

    summary_client = FakeLlmClient(
        {
            "summaries": [
                {
                    "title": "Executive Summary",
                    "summary_type": "executive",
                    "content": "The team agreed to keep the release local-first.",
                    "evidence_snippet": "Decision: we will keep the release local-first.",
                },
                {
                    "title": "Detailed Summary",
                    "summary_type": "detailed",
                    "content": "The meeting focused on a local-first release plan and follow-up validation work.",
                    "evidence_snippet": "Action item: Speaker 1 will prepare the rollout checklist.",
                },
            ]
        }
    )
    action_client = FakeLlmClient(
        {
            "actions": [
                {
                    "description": "Prepare the rollout checklist.",
                    "owner_name": "Speaker 1",
                    "evidence_snippet": "Action item: Speaker 1 will prepare the rollout checklist.",
                    "start_offset_seconds": 0,
                    "end_offset_seconds": 6,
                }
            ],
            "decisions": [
                {
                    "description": "Keep the release local-first.",
                    "evidence_snippet": "Decision: we will keep the release local-first.",
                    "start_offset_seconds": 0,
                    "end_offset_seconds": 4,
                }
            ],
            "follow_ups": [
                {
                    "description": "Determine whether extra validation is needed.",
                    "follow_up_type": "open_question",
                    "owner_name": "Unconfirmed speaker",
                    "evidence_snippet": "Open question: do we need extra validation for the blocker risk?",
                    "start_offset_seconds": 5,
                    "end_offset_seconds": 10,
                }
            ],
        }
    )

    summaries = SummarizerService(config, llm_client=summary_client)
    summary_result = summaries.generate_summaries("capture-llm", provider_name="local_llm")
    summary_rows = summaries.list_summaries("capture-llm")

    extractor = ActionExtractorService(config, llm_client=action_client)
    extraction_result = extractor.extract_capture("capture-llm", provider_name="local_llm")
    outputs = extractor.list_outputs("capture-llm")

    assert summary_result["provider_name"] == "local_llm"
    assert summary_result["model_name"] == "llama3.1:8b"
    assert all(row["provider_name"] == "local_llm" for row in summary_rows)
    assert all(row["model_name"] == "llama3.1:8b" for row in summary_rows)
    assert extraction_result["provider_name"] == "local_llm"
    assert outputs["actions"][0]["provider_name"] == "local_llm"
    assert outputs["actions"][0]["model_name"] == "llama3.1:8b"
    assert outputs["decisions"][0]["provider_name"] == "local_llm"
    assert outputs["follow_ups"][0]["provider_name"] == "local_llm"


def test_local_llm_invalid_json_falls_back_to_heuristic(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_transcript(config)

    class InvalidPayloadClient:
        def generate_json(self, prompt: str) -> dict[str, object]:
            del prompt
            return {"not_summaries": []}

    summaries = SummarizerService(config, llm_client=InvalidPayloadClient())
    result = summaries.generate_summaries("capture-llm", provider_name="local_llm")
    rows = summaries.list_summaries("capture-llm")

    assert result["provider_name"] == "heuristic"
    assert all(row["provider_name"] == "heuristic" for row in rows)


def test_local_llm_timeout_falls_back_to_heuristic_for_actions(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_transcript(config)

    extractor = ActionExtractorService(config, llm_client=FailingLlmClient())
    result = extractor.extract_capture("capture-llm", provider_name="local_llm")
    outputs = extractor.list_outputs("capture-llm")

    assert result["provider_name"] == "heuristic"
    assert outputs["actions"][0]["provider_name"] == "heuristic"
