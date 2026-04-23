from __future__ import annotations

import wave
from pathlib import Path

from local_meeting_notes.action_extractor.service import ActionExtractorService
from local_meeting_notes.config import load_config
from local_meeting_notes.local_llm import LocalLlmClientError
from local_meeting_notes.local_llm.transcript_cleaning import (
    clean_transcript_segments,
    format_clean_transcript_context,
)
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
                    "content": "Speaker 1 will prepare the rollout checklist.",
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


def test_transcript_cleaning_suppresses_asr_noise() -> None:
    segments = [
        {
            "speaker_label": "Unknown",
            "content": "um um um yeah yeah [inaudible] background noise",
            "start_offset_seconds": 0,
            "end_offset_seconds": 1,
        },
        {
            "speaker_label": "Speaker 1",
            "content": "Action item action item: please prepare the release checklist checklist.",
            "start_offset_seconds": 2,
            "end_offset_seconds": 8,
        },
        {
            "speaker_label": "Speaker 1",
            "content": "Action item action item: please prepare the release checklist checklist.",
            "start_offset_seconds": 9,
            "end_offset_seconds": 12,
        },
    ]

    cleaned = clean_transcript_segments(segments)
    context = format_clean_transcript_context(segments, max_chars=1000)

    assert len(cleaned) == 1
    assert "um um" not in context
    assert "background noise" not in context
    assert "checklist checklist" not in context
    assert "please prepare the release checklist" in context


def test_local_llm_prompt_uses_cleaned_transcript_context(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_transcript(config)

    class CapturingSummaryClient:
        prompt = ""

        def generate_json(self, prompt: str) -> dict[str, object]:
            self.prompt = prompt
            return {
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
                        "content": "The team agreed to keep the release local-first and prepare validation follow-up work.",
                        "evidence_snippet": "Action item: Speaker 1 will prepare the rollout checklist.",
                    },
                ]
            }

    client = CapturingSummaryClient()
    summaries = SummarizerService(config, llm_client=client)
    summaries.generate_summaries("capture-llm", provider_name="local_llm")

    assert "Ignore garbled or weakly supported items" in client.prompt
    assert "Return JSON only." in client.prompt


def test_malformed_decision_output_is_suppressed(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_transcript(config)

    client = FakeLlmClient(
        {
            "actions": [],
            "decisions": [
                {
                    "description": "Approve the enterprise migration.",
                    "evidence_snippet": "garbled migration maybe maybe inaudible",
                    "start_offset_seconds": 0,
                    "end_offset_seconds": 1,
                }
            ],
            "follow_ups": [],
        }
    )

    extractor = ActionExtractorService(config, llm_client=client)
    result = extractor.extract_capture("capture-llm", provider_name="local_llm")
    outputs = extractor.list_outputs("capture-llm")

    assert result["decisions"] == 0
    assert outputs["decisions"] == []


def test_weak_local_llm_summary_output_falls_back_to_heuristic(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_transcript(config)

    client = FakeLlmClient(
        {
            "summaries": [
                {
                    "title": "Executive Summary",
                    "summary_type": "executive",
                    "content": "Approve the enterprise migration.",
                    "evidence_snippet": "Decision: we will keep the release local-first.",
                },
                {
                    "title": "Detailed Summary",
                    "summary_type": "detailed",
                    "content": "Approve the enterprise migration and cloud deployment.",
                    "evidence_snippet": "Action item: Speaker 1 will prepare the rollout checklist.",
                },
            ]
        }
    )

    summaries = SummarizerService(config, llm_client=client)
    result = summaries.generate_summaries("capture-llm", provider_name="local_llm")
    rows = summaries.list_summaries("capture-llm")

    assert result["provider_name"] == "heuristic"
    assert all(row["provider_name"] == "heuristic" for row in rows)
