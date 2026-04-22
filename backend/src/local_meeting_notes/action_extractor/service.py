"""Action, decision, and follow-up extraction service."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import ActionRecord, DecisionRecord, FollowUpRecord
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
from .providers import HeuristicActionExtractionProvider


class ActionExtractorService:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        provider: HeuristicActionExtractionProvider | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.action_extractor")
        self._provider = provider or HeuristicActionExtractionProvider()

    def extract_capture(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, capture_id)
            transcript_rows = fetch_transcript_segments_for_capture(connection, capture_id)
            if not transcript_rows:
                raise RuntimeError(f"No transcript segments found for capture '{capture_id}'.")

            delete_actions_for_capture(connection, capture_id)
            delete_decisions_for_capture(connection, capture_id)
            delete_follow_ups_for_capture(connection, capture_id)

            actions, decisions, follow_ups = self._provider.extract([dict(row) for row in transcript_rows])

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
                    ),
                )

            connection.commit()

        return {
            "capture_id": capture_id,
            "actions": len(actions),
            "decisions": len(decisions),
            "follow_ups": len(follow_ups),
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
