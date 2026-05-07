"""Action, decision, and follow-up extraction service."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import ActionRecord, DecisionRecord, FollowUpRecord
from ..quality_guardrails import assess_extracted_item
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    delete_actions_for_capture,
    delete_decisions_for_capture,
    delete_follow_ups_for_capture,
    ensure_meeting_for_capture,
    fetch_actions_for_capture,
    fetch_decisions_for_capture,
    fetch_follow_ups_for_capture,
    fetch_transcript_segments_for_capture,
    insert_action,
    insert_decision,
    insert_follow_up,
)
from .providers import build_action_extraction_provider


class ActionExtractorService:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        provider=None,
        llm_client=None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.action_extractor")
        self._provider = provider
        self._llm_client = llm_client

    def _resolve_provider(self, provider_name: str | None = None):
        if self._provider is not None and provider_name is None:
            return self._provider
        target = provider_name or self.config.action_extraction_provider
        return build_action_extraction_provider(
            self.config,
            provider_name=target,
            logger=self.logger,
            client=self._llm_client,
        )

    def extract_capture(self, capture_id: str, provider_name: str | None = None) -> dict[str, object]:
        bootstrap_database(self.config)
        provider = self._resolve_provider(provider_name)
        with connection_context(self.config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, capture_id)
            transcript_rows = fetch_transcript_segments_for_capture(connection, capture_id)
            if not transcript_rows:
                raise RuntimeError(f"No transcript segments found for capture '{capture_id}'.")

            existing_outputs = [
                *[dict(row) for row in fetch_actions_for_capture(connection, capture_id)],
                *[dict(row) for row in fetch_decisions_for_capture(connection, capture_id)],
                *[dict(row) for row in fetch_follow_ups_for_capture(connection, capture_id)],
            ]
            if _has_reviewed_outputs(existing_outputs):
                raise RuntimeError(
                    "Cannot re-extract outcomes because reviewed items exist for this capture. "
                    "Export or reset review state before reprocessing."
                )

            delete_actions_for_capture(connection, capture_id)
            delete_decisions_for_capture(connection, capture_id)
            delete_follow_ups_for_capture(connection, capture_id)

            actions, decisions, follow_ups = provider.extract([dict(row) for row in transcript_rows])
            actions = [
                item
                for item in actions
                if assess_extracted_item(item.description, item.evidence_snippet).is_acceptable
            ]
            decisions = [
                item
                for item in decisions
                if assess_extracted_item(item.description, item.evidence_snippet).is_acceptable
            ]
            follow_ups = [
                item
                for item in follow_ups
                if assess_extracted_item(item.description, item.evidence_snippet).is_acceptable
            ]

            for item in actions:
                insert_action(
                    connection,
                    ActionRecord(
                        id=None,
                        meeting_id=meeting_id,
                        capture_id=capture_id,
                        description=item.description,
                        owner_name=item.owner_name,
                        status="open",
                        evidence_snippet=item.evidence_snippet,
                        start_offset_seconds=item.start_offset_seconds,
                        end_offset_seconds=item.end_offset_seconds,
                        provider_name=item.provider_name,
                        model_name=item.model_name,
                        generated_at=item.generated_at,
                    ),
                )

            for item in decisions:
                insert_decision(
                    connection,
                    DecisionRecord(
                        id=None,
                        meeting_id=meeting_id,
                        description=item.description,
                        capture_id=capture_id,
                        evidence_snippet=item.evidence_snippet,
                        start_offset_seconds=item.start_offset_seconds,
                        end_offset_seconds=item.end_offset_seconds,
                        provider_name=item.provider_name,
                        model_name=item.model_name,
                        generated_at=item.generated_at,
                    ),
                )

            for item in follow_ups:
                insert_follow_up(
                    connection,
                    FollowUpRecord(
                        id=None,
                        meeting_id=meeting_id,
                        capture_id=capture_id,
                        description=item.description,
                        follow_up_type=item.follow_up_type,
                        owner_name=item.owner_name,
                        status="open",
                        evidence_snippet=item.evidence_snippet,
                        start_offset_seconds=item.start_offset_seconds,
                        end_offset_seconds=item.end_offset_seconds,
                        provider_name=item.provider_name,
                        model_name=item.model_name,
                        generated_at=item.generated_at,
                    ),
                )

            connection.commit()

        return {
            "capture_id": capture_id,
            "actions": len(actions),
            "decisions": len(decisions),
            "follow_ups": len(follow_ups),
            "provider_name": (
                actions[0].provider_name
                if actions
                else decisions[0].provider_name
                if decisions
                else follow_ups[0].provider_name
                if follow_ups
                else (provider_name or self.config.action_extraction_provider)
            ),
            "model_name": (
                actions[0].model_name
                if actions
                else decisions[0].model_name
                if decisions
                else follow_ups[0].model_name
                if follow_ups
                else None
            ),
        }

    def list_outputs(self, capture_id: str) -> dict[str, list[dict[str, object]]]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            actions = fetch_actions_for_capture(connection, capture_id)
            decisions = fetch_decisions_for_capture(connection, capture_id)
            follow_ups = fetch_follow_ups_for_capture(connection, capture_id)
        return {
            "actions": [dict(row) for row in actions],
            "decisions": [dict(row) for row in decisions],
            "follow_ups": [dict(row) for row in follow_ups],
        }


def _has_reviewed_outputs(items: list[dict[str, object]]) -> bool:
    return any(
        item.get("reviewed_at")
        or str(item.get("review_status") or "generated") in {"accepted", "edited", "rejected"}
        for item in items
    )
