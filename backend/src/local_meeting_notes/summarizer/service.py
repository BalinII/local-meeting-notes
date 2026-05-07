"""Summary generation service for transcript-backed capture summaries."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import SummaryRecord
from ..quality_guardrails import assess_summary_text
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    delete_summaries_for_capture,
    ensure_meeting_for_capture,
    fetch_summaries_for_capture,
    fetch_transcript_segments_for_capture,
    insert_summary,
)
from .providers import build_summary_provider


class SummarizerService:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        provider=None,
        llm_client=None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.summarizer")
        self._provider = provider
        self._llm_client = llm_client

    def _resolve_provider(self, provider_name: str | None = None):
        if self._provider is not None and provider_name is None:
            return self._provider
        target = provider_name or self.config.summary_provider
        return build_summary_provider(
            self.config,
            provider_name=target,
            logger=self.logger,
            client=self._llm_client,
        )

    def generate_summaries(self, capture_id: str, provider_name: str | None = None) -> dict[str, object]:
        bootstrap_database(self.config)
        provider = self._resolve_provider(provider_name)
        with connection_context(self.config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, capture_id)
            transcript_rows = fetch_transcript_segments_for_capture(connection, capture_id)
            if not transcript_rows:
                raise RuntimeError(f"No transcript segments found for capture '{capture_id}'.")

            delete_summaries_for_capture(connection, capture_id)
            drafts = provider.build_summaries(capture_id, [dict(row) for row in transcript_rows])
            drafts = [
                draft
                for draft in drafts
                if assess_summary_text(draft.content, draft.evidence_snippet).is_acceptable
            ]
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
                        provider_name=draft.provider_name,
                        model_name=draft.model_name,
                        generated_at=draft.generated_at,
                    ),
                )
            connection.commit()

        return {
            "capture_id": capture_id,
            "summary_count": len(drafts),
            "provider_name": drafts[0].provider_name if drafts else (provider_name or self.config.summary_provider),
            "model_name": drafts[0].model_name if drafts else None,
        }

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
                "provider_name": row["provider_name"],
                "model_name": row["model_name"],
                "generated_at": row["generated_at"],
            }
            for row in rows
        ]
