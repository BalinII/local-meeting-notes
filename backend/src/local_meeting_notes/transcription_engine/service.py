"""Batch local transcription service for captured audio chunks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from soundfile import info as soundfile_info  # type: ignore

from ..config import AppConfig
from ..models import TranscriptSegmentRecord
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    delete_transcript_segments_for_capture,
    ensure_meeting_for_capture,
    fetch_transcript_segments_for_capture,
    fetch_transcription_status,
    insert_transcript_segment,
)
from .providers import (
    TranscriptionDependencyError,
    TranscriptionProvider,
    build_transcription_provider,
)


@dataclass(slots=True)
class AudioChunk:
    path: Path
    start_offset_seconds: int
    end_offset_seconds: int


class TranscriptionEngineService:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        provider: TranscriptionProvider | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.transcription")
        self._provider = provider

    def _provider_instance(self) -> TranscriptionProvider:
        if self._provider is None:
            self._provider = build_transcription_provider(self.config)
        return self._provider

    def discover_chunks(self, capture_id: str) -> list[AudioChunk]:
        capture_dir = self.config.audio_output_dir / capture_id
        chunk_paths = sorted(capture_dir.rglob("*.wav"))
        chunks: list[AudioChunk] = []
        offset = 0
        for chunk_path in chunk_paths:
            duration = max(1, int(round(soundfile_info(str(chunk_path)).duration)))
            chunks.append(
                AudioChunk(
                    path=chunk_path,
                    start_offset_seconds=offset,
                    end_offset_seconds=offset + duration,
                )
            )
            offset += duration
        return chunks

    def transcribe_capture(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        chunks = self.discover_chunks(capture_id)
        if not chunks:
            raise RuntimeError(f"No audio chunks found for capture '{capture_id}'.")

        provider = self._provider_instance()
        completed = 0
        failed = 0

        with connection_context(self.config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, capture_id)
            delete_transcript_segments_for_capture(connection, capture_id)

            for chunk in chunks:
                relative_path = chunk.path.resolve().relative_to(self.config.data_dir.resolve())
                try:
                    result = provider.transcribe_file(chunk.path)
                    segment = TranscriptSegmentRecord(
                        id=None,
                        meeting_id=meeting_id,
                        capture_id=capture_id,
                        source_chunk_path=str(relative_path),
                        transcription_status="completed",
                        speaker_label="Unknown",
                        content=result.text,
                        start_offset_seconds=chunk.start_offset_seconds,
                        end_offset_seconds=chunk.end_offset_seconds,
                        provider_name=result.provider_name,
                        model_name=result.model_name,
                        error_message=None,
                        is_mock=False,
                    )
                    completed += 1
                    self.logger.info("Transcribed chunk %s", chunk.path)
                except Exception as exc:
                    segment = TranscriptSegmentRecord(
                        id=None,
                        meeting_id=meeting_id,
                        capture_id=capture_id,
                        source_chunk_path=str(relative_path),
                        transcription_status="failed",
                        speaker_label="Unknown",
                        content="",
                        start_offset_seconds=chunk.start_offset_seconds,
                        end_offset_seconds=chunk.end_offset_seconds,
                        provider_name=self.config.transcription_provider,
                        model_name=self.config.transcription_model_size,
                        error_message=str(exc),
                        is_mock=False,
                    )
                    failed += 1
                    self.logger.exception("Failed to transcribe chunk %s", chunk.path)

                insert_transcript_segment(connection, segment)

            connection.commit()

        return {
            "capture_id": capture_id,
            "total_chunks": len(chunks),
            "completed_chunks": completed,
            "failed_chunks": failed,
        }

    def get_status(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = fetch_transcription_status(connection, capture_id)
        if row is None:
            return {
                "capture_id": capture_id,
                "status": "not_started",
                "total_segments": 0,
                "completed_segments": 0,
                "failed_segments": 0,
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
            rows = fetch_transcript_segments_for_capture(connection, capture_id)
        return [
            {
                "capture_id": row["capture_id"],
                "source_chunk_path": row["source_chunk_path"],
                "transcription_status": row["transcription_status"],
                "start_offset_seconds": row["start_offset_seconds"],
                "end_offset_seconds": row["end_offset_seconds"],
                "content": row["content"],
                "error_message": row["error_message"],
            }
            for row in rows
        ]
