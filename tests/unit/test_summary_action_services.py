from __future__ import annotations

import wave
from pathlib import Path

from local_meeting_notes.action_extractor.service import ActionExtractorService
from local_meeting_notes.action_extractor.providers import ExtractedAction
from local_meeting_notes.config import load_config
from local_meeting_notes.export_service.service import ExportService
from local_meeting_notes.summarizer.providers import SummaryDraft
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
            "SUMMARY_PROVIDER": "heuristic",
            "ACTION_EXTRACTION_PROVIDER": "heuristic",
            "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11434",
            "LOCAL_LLM_MODEL": "llama3.1:8b",
            "LOCAL_LLM_TIMEOUT_SECONDS": "10",
            "LOCAL_LLM_MAX_TRANSCRIPT_CHARS": "8000",
        }
    )


def _write_wav(path: Path, seconds: int = 1, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * sample_rate * seconds)


class FakeTranscriptProvider:
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        name = chunk_path.name
        if "001" in name:
            text = "Speaker one update. Decision: we will keep the rollout local-first."
        elif "002" in name:
            text = "Action item: please prepare the draft plan by Friday."
        else:
            text = "Open question: do we need extra testing for the blocker risk?"
        return TranscriptionResult(text=text, provider_name="fake", model_name="fake")


class GarbledSummaryProvider:
    def build_summaries(self, capture_id: str, transcript_segments: list[dict[str, object]]) -> list[SummaryDraft]:
        del capture_id, transcript_segments
        return [
            SummaryDraft(
                title="Executive Summary",
                summary_type="executive",
                content="Noise noise noise noise noise noise noise noise.",
                evidence_snippet="noise noise",
            ),
            SummaryDraft(
                title="Detailed Summary",
                summary_type="detailed",
                content="What can find only remains the surface to fault and cross procession work for them.",
                evidence_snippet="what can find only remains",
            ),
        ]


class WeakActionProvider:
    def extract(self, transcript_segments: list[dict[str, object]]):
        del transcript_segments
        return [
            ExtractedAction(
                description="Approve unrelated migration.",
                owner_name="Speaker 1",
                evidence_snippet="garbled migration maybe maybe inaudible",
                start_offset_seconds=0,
                end_offset_seconds=1,
            )
        ], [], []


def test_summary_and_action_services_persist_outputs(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    capture_dir = config.audio_output_dir / "capture-phase6" / "microphone"
    _write_wav(capture_dir / "chunk_001.wav")
    _write_wav(capture_dir / "chunk_002.wav")
    _write_wav(capture_dir / "chunk_003.wav")

    transcription = TranscriptionEngineService(config, provider=FakeTranscriptProvider())
    transcription.transcribe_capture("capture-phase6")

    summaries = SummarizerService(config)
    summary_result = summaries.generate_summaries("capture-phase6")
    summary_rows = summaries.list_summaries("capture-phase6")

    extractor = ActionExtractorService(config)
    extraction_result = extractor.extract_capture("capture-phase6")
    outputs = extractor.list_outputs("capture-phase6")

    assert summary_result["summary_count"] == 2
    assert len(summary_rows) == 2
    assert any(row["summary_type"] == "executive" for row in summary_rows)
    assert extraction_result["actions"] >= 1
    assert extraction_result["decisions"] >= 1
    assert extraction_result["follow_ups"] >= 1
    assert outputs["actions"][0]["owner_name"] in {"Unknown", "Speaker 1", "Speaker 2", "Unconfirmed speaker"}
    assert outputs["decisions"][0]["evidence_snippet"]
    assert outputs["follow_ups"][0]["follow_up_type"] in {"follow_up", "blocker_risk", "open_question"}
    assert all(row["provider_name"] == "heuristic" for row in summary_rows)
    assert all(item["provider_name"] == "heuristic" for item in outputs["actions"])


def test_action_extraction_blocks_rerun_when_reviewed_items_exist(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    capture_dir = config.audio_output_dir / "capture-reviewed" / "microphone"
    _write_wav(capture_dir / "chunk_001.wav")
    _write_wav(capture_dir / "chunk_002.wav")

    transcription = TranscriptionEngineService(config, provider=FakeTranscriptProvider())
    transcription.transcribe_capture("capture-reviewed")

    extractor = ActionExtractorService(config)
    extractor.extract_capture("capture-reviewed")
    payload = ExportService(config).build_review_payload("capture-reviewed")
    action_id = payload["actions"][0]["id"]
    ExportService(config).review_item(
        item_type="action",
        item_id=action_id,
        review_status="accepted",
    )

    try:
        extractor.extract_capture("capture-reviewed")
    except RuntimeError as exc:
        assert "reviewed items exist" in str(exc)
    else:
        raise AssertionError("Re-extraction should not erase reviewed output")


def test_summary_service_suppresses_obviously_bad_generated_summaries(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    capture_dir = config.audio_output_dir / "capture-bad-summary" / "microphone"
    _write_wav(capture_dir / "chunk_001.wav")
    TranscriptionEngineService(config, provider=FakeTranscriptProvider()).transcribe_capture("capture-bad-summary")

    summaries = SummarizerService(config, provider=GarbledSummaryProvider())
    result = summaries.generate_summaries("capture-bad-summary")
    rows = summaries.list_summaries("capture-bad-summary")

    assert result["summary_count"] == 0
    assert rows == []


def test_action_extraction_suppresses_weak_generated_items(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    capture_dir = config.audio_output_dir / "capture-weak-action" / "microphone"
    _write_wav(capture_dir / "chunk_001.wav")
    TranscriptionEngineService(config, provider=FakeTranscriptProvider()).transcribe_capture("capture-weak-action")

    extractor = ActionExtractorService(config, provider=WeakActionProvider())
    result = extractor.extract_capture("capture-weak-action")
    outputs = extractor.list_outputs("capture-weak-action")

    assert result["actions"] == 0
    assert outputs["actions"] == []
