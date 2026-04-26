from pathlib import Path

import pytest

from local_meeting_notes.config import load_config
from local_meeting_notes.transcription_engine.service import TranscriptionEngineService


def test_transcription_discovers_chunks_in_numeric_prefix_order(local_tmp_dir, monkeypatch) -> None:
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
    capture_dir = config.audio_output_dir / "capture-order"
    (capture_dir / "microphone").mkdir(parents=True, exist_ok=True)
    ordered = [
      capture_dir / "microphone" / "000002_20260425T000001Z_microphone.wav",
      capture_dir / "microphone" / "000001_20260425T000000Z_microphone.wav",
      capture_dir / "microphone" / "000003_20260425T000002Z_microphone.wav",
    ]
    for path in ordered:
        path.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(
        "local_meeting_notes.transcription_engine.service.soundfile_info",
        lambda _: type("Info", (), {"duration": 1.0})(),
    )

    chunks = TranscriptionEngineService(config).discover_chunks("capture-order")

    assert [Path(chunk.path).name for chunk in chunks] == [
        "000001_20260425T000000Z_microphone.wav",
        "000002_20260425T000001Z_microphone.wav",
        "000003_20260425T000002Z_microphone.wav",
    ]
    assert chunks[0].start_offset_seconds == 0
    assert chunks[1].start_offset_seconds == 1
    assert chunks[2].start_offset_seconds == 2


def test_transcription_rejects_parallel_source_timelines(local_tmp_dir, monkeypatch) -> None:
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
    capture_dir = config.audio_output_dir / "capture-parallel"
    paths = [
        capture_dir / "microphone" / "000001_20260425T000000Z_microphone.wav",
        capture_dir / "loopback" / "000002_20260425T000000Z_loopback.wav",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(
        "local_meeting_notes.transcription_engine.service.soundfile_info",
        lambda _: type("Info", (), {"duration": 1.0})(),
    )

    with pytest.raises(RuntimeError, match="Multiple parallel audio sources"):
        TranscriptionEngineService(config).discover_chunks("capture-parallel")
