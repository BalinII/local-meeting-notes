"""Batch diarization service for captured audio and transcript alignment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from soundfile import info as soundfile_info  # type: ignore

from ..config import AppConfig
from ..models import DiarizationSegmentRecord
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    apply_speaker_labels_to_transcript_segments,
    delete_diarization_segments_for_capture,
    ensure_meeting_for_capture,
    fetch_diarization_segments_for_capture,
    fetch_diarization_status,
    insert_diarization_segment,
)
from .providers import DiarizationProvider, build_diarization_provider


@dataclass(slots=True)
class AudioChunkReference:
    path: Path
    start_offset_seconds: int
    end_offset_seconds: int


class DiarizationEngineService:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        provider: DiarizationProvider | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.diarization")
        self._provider = provider

    def _provider_instance(self) -> DiarizationProvider:
        if self._provider is None:
            self._provider = build_diarization_provider(self.config)
        return self._provider

    def discover_audio_files(self, capture_id: str) -> list[AudioChunkReference]:
        capture_dir = self.config.audio_output_dir / capture_id
        chunk_paths = sorted(capture_dir.rglob("*.wav"))
        chunks: list[AudioChunkReference] = []
        offset = 0
        for chunk_path in chunk_paths:
            duration = max(1, int(round(soundfile_info(str(chunk_path)).duration)))
            chunks.append(
                AudioChunkReference(
                    path=chunk_path,
                    start_offset_seconds=offset,
                    end_offset_seconds=offset + duration,
                )
            )
            offset += duration
        return chunks

    def diarize_capture(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        audio_files = self.discover_audio_files(capture_id)
        if not audio_files:
            raise RuntimeError(f"No audio chunks found for capture '{capture_id}'.")

        provider = self._provider_instance()
        completed = 0
        failed = 0

        with connection_context(self.config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, capture_id)
            delete_diarization_segments_for_capture(connection, capture_id)

            for audio_file in audio_files:
                relative_path = audio_file.path.resolve().relative_to(self.config.data_dir.resolve())
                try:
                    segments = provider.diarize_file(audio_file.path)
                    if not segments:
                        segments = []
                    for segment in segments:
                        insert_diarization_segment(
                            connection,
                            DiarizationSegmentRecord(
                                id=None,
                                meeting_id=meeting_id,
                                capture_id=capture_id,
                                source_audio_path=str(relative_path),
                                diarization_status="completed",
                                speaker_label=segment.speaker_label,
                                start_offset_seconds=audio_file.start_offset_seconds
                                + segment.start_offset_seconds,
                                end_offset_seconds=audio_file.start_offset_seconds
                                + segment.end_offset_seconds,
                                provider_name=self.config.diarization_provider,
                                confidence=segment.confidence,
                                error_message=None,
                            ),
                        )
                    completed += 1
                    self.logger.info("Diarized audio file %s", audio_file.path)
                except Exception as exc:
                    insert_diarization_segment(
                        connection,
                        DiarizationSegmentRecord(
                            id=None,
                            meeting_id=meeting_id,
                            capture_id=capture_id,
                            source_audio_path=str(relative_path),
                            diarization_status="failed",
                            speaker_label="Unknown",
                            start_offset_seconds=audio_file.start_offset_seconds,
                            end_offset_seconds=audio_file.start_offset_seconds,
                            provider_name=self.config.diarization_provider,
                            confidence=None,
                            error_message=str(exc),
                        ),
                    )
                    failed += 1
                    self.logger.exception("Failed to diarize audio file %s", audio_file.path)

            apply_speaker_labels_to_transcript_segments(connection, capture_id)
            connection.commit()

        return {
            "capture_id": capture_id,
            "total_audio_files": len(audio_files),
            "completed_audio_files": completed,
            "failed_audio_files": failed,
        }

    def get_status(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = fetch_diarization_status(connection, capture_id)
        if row is None:
            return {
                "capture_id": capture_id,
                "status": "not_started",
                "total_segments": 0,
                "completed_segments": 0,
                "failed_segments": 0,
                "pending_segments": 0,
            }
        overall_status = "failed" if row["failed_segments"] else "completed"
        if row["pending_segments"]:
            overall_status = "pending"
        return {
            "capture_id": capture_id,
            "status": overall_status,
            "total_segments": row["total_segments"],
            "completed_segments": row["completed_segments"] or 0,
            "failed_segments": row["failed_segments"] or 0,
            "pending_segments": row["pending_segments"] or 0,
        }

    def list_segments(self, capture_id: str) -> list[dict[str, object]]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            rows = fetch_diarization_segments_for_capture(connection, capture_id)
        return [
            {
                "capture_id": row["capture_id"],
                "source_audio_path": row["source_audio_path"],
                "diarization_status": row["diarization_status"],
                "speaker_label": row["speaker_label"],
                "start_offset_seconds": row["start_offset_seconds"],
                "end_offset_seconds": row["end_offset_seconds"],
                "confidence": row["confidence"],
                "error_message": row["error_message"],
            }
            for row in rows
        ]
