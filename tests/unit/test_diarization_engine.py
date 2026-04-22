from __future__ import annotations

import wave
from pathlib import Path

from local_meeting_notes.config import load_config
from local_meeting_notes.diarization_engine.providers import (
    DiarizationResultSegment,
    _finalise_segments,
    _merge_adjacent_same_speaker_segments,
)
from local_meeting_notes.diarization_engine.service import DiarizationEngineService
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


class FakeTranscriptionProvider:
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        return TranscriptionResult(
            text=f"text for {chunk_path.name}",
            provider_name="fake-transcription",
            model_name="fake-model",
        )


class FakeDiarizationProvider:
    def diarize_file(self, audio_path: Path) -> list[DiarizationResultSegment]:
        return [
            DiarizationResultSegment(
                start_offset_seconds=0,
                end_offset_seconds=1,
                speaker_label="Speaker 1",
                confidence=None,
            )
        ]


def test_diarization_persists_segments_and_labels_transcript(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    capture_dir = config.audio_output_dir / "capture-5678" / "microphone"
    _write_wav(capture_dir / "chunk_001.wav")

    transcription = TranscriptionEngineService(config, provider=FakeTranscriptionProvider())
    transcription.transcribe_capture("capture-5678")

    diarization = DiarizationEngineService(config, provider=FakeDiarizationProvider())
    result = diarization.diarize_capture("capture-5678")
    status = diarization.get_status("capture-5678")
    diarization_segments = diarization.list_segments("capture-5678")
    transcript_segments = transcription.list_segments("capture-5678")

    assert result["completed_audio_files"] == 1
    assert status["status"] == "completed"
    assert diarization_segments[0]["speaker_label"] == "Speaker 1"
    assert transcript_segments[0]["speaker_label"] == "Speaker 1"


def test_merge_adjacent_same_speaker_segments() -> None:
    segments = [
        DiarizationResultSegment(0.0, 1.0, "Speaker 1"),
        DiarizationResultSegment(1.2, 2.0, "Speaker 1"),
        DiarizationResultSegment(3.0, 4.0, "Speaker 2"),
    ]

    merged = _merge_adjacent_same_speaker_segments(segments, max_gap_seconds=0.3)

    assert len(merged) == 2
    assert merged[0].speaker_label == "Speaker 1"
    assert merged[0].start_offset_seconds == 0.0
    assert merged[0].end_offset_seconds == 2.0


def test_finalise_segments_reduces_micro_fragmentation() -> None:
    segments = [
        DiarizationResultSegment(0.0, 2.0, "Speaker 1"),
        DiarizationResultSegment(2.0, 2.4, "Speaker 2"),
        DiarizationResultSegment(2.4, 5.0, "Speaker 1"),
    ]

    stable = _finalise_segments(segments)

    assert len(stable) == 1
    assert stable[0].speaker_label == "Speaker 1"
    assert stable[0].start_offset_seconds == 0.0
    assert stable[0].end_offset_seconds == 5.0
