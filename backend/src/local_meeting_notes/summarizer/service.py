"""Summary generation service for transcript-backed capture summaries."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import SummaryRecord
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    delete_summaries_for_capture,
    ensure_meeting_for_capture,
    fetch_summaries_for_capture,
    fetch_transcript_segments_for_capture,
    insert_summary,
)
from .providers import HeuristicSummaryProvider


class SummarizerService:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        provider: HeuristicSummaryProvider | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.summarizer")
        self._provider = provider or HeuristicSummaryProvider()

    def generate_summaries(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, capture_id)
            transcript_rows = fetch_transcript_segments_for_capture(connection, capture_id)
            if not transcript_rows:
                raise RuntimeError(f"No transcript segments found for capture '{capture_id}'.")

            delete_summaries_for_capture(connection, capture_id)
            drafts = self._provider.build_summaries(capture_id, [dict(row) for row in transcript_rows])
            for draft in drafts:
                insert_summary(
                    connection,
                    SummaryRecord(
                        id=None,
                        meeting_id=meeting_id,
                        capture_id=capture_id,
                        title=draft.title,
                        content=draft.content,
                        summary_type=draft.summary_type,
                        evidence_snippet=draft.evidence_snippet,
                    ),
                )
            connection.commit()

        return {"capture_id": capture_id, "summary_count": len(drafts)}

    def list_summaries(self, capture_id: str) -> list[dict[str, object]]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            rows = fetch_summaries_for_capture(connection, capture_id)
        return [
            {
                "title": row["title"],
                "summary_type": row["summary_type"],
                "content": row["content"],
                "evidence_snippet": row["evidence_snippet"],
            }
            for row in rows
        ]
