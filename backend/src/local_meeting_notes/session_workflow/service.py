"""Local recording session workflow and retention management."""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ..action_extractor.service import ActionExtractorService
from ..audio_capture.service import AudioCaptureService
from ..config import AppConfig
from ..diarization_engine.service import DiarizationEngineService
from ..export_service.service import ExportService
from ..microsoft_integration.service import MicrosoftIntegrationService
from ..models import MeetingRecord
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    fetch_app_settings,
    fetch_cross_session_action_items,
    fetch_session_library_rows,
    search_capture_content,
    fetch_meeting_by_capture_id,
    fetch_recent_meetings,
    insert_meeting,
    update_meeting_fields,
    update_workspace_item_status,
    update_workspace_item_details,
    upsert_app_setting,
)
from ..summarizer.service import SummarizerService
from ..transcription_engine.service import TranscriptionEngineService


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _utc_iso() -> str:
    return _utc_now().isoformat()


class SessionWorkflowService:
    allowed_transitions = {
        "draft": {"recording", "archived"},
        "recording": {"paused", "processing"},
        "paused": {"recording", "processing", "archived"},
        "processing": {"review_ready", "processing_failed"},
        "processing_failed": {"processing", "archived"},
        "review_ready": {"reviewed", "final", "exported", "archived", "recording"},
        "reviewed": {"final", "exported", "archived", "recording"},
        "final": {"exported", "archived", "recording"},
        "exported": {"archived", "recording"},
        "archived": set(),
    }

    def __init__(
        self,
        config: AppConfig,
        *,
        audio_capture: AudioCaptureService,
        transcription_engine: TranscriptionEngineService,
        diarization_engine: DiarizationEngineService,
        summarizer: SummarizerService,
        action_extractor: ActionExtractorService,
        export_service: ExportService,
        microsoft_integration: MicrosoftIntegrationService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.audio_capture = audio_capture
        self.transcription_engine = transcription_engine
        self.diarization_engine = diarization_engine
        self.summarizer = summarizer
        self.action_extractor = action_extractor
        self.export_service = export_service
        self.microsoft_integration = microsoft_integration
        self.logger = logger or logging.getLogger("local_meeting_notes.session_workflow")

    def dashboard_payload(self) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            sessions = [self._hydrate_session(dict(row)) for row in fetch_recent_meetings(connection)]
            action_items = [
                _hydrate_workspace_item(dict(row))
                for row in fetch_cross_session_action_items(connection)
            ]
            settings = self._settings_with_defaults(fetch_app_settings(connection))
        active_capture = self.audio_capture.status()
        return {
            "sessions": sessions,
            "action_items": action_items,
            "settings": settings,
            "active_capture": active_capture if active_capture.get("capture_id") else None,
        }

    def action_workspace(
        self,
        *,
        limit: int = 200,
        workflow_filter: str = "active",
        sort: str = "recent",
    ) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            rows = [dict(row) for row in fetch_cross_session_action_items(connection, limit=max(limit, 500))]
        items = [
            item for item in (_hydrate_workspace_item(row) for row in rows)
            if item["item_type"] in {"action", "follow_up"}
        ]
        filtered = _filter_action_workspace_items(items, workflow_filter)
        sorted_items = _sort_action_workspace_items(filtered, sort)
        safe_limit = max(1, min(int(limit), 500))
        return {
            "items": sorted_items[:safe_limit],
            "filter": _normalize_action_filter(workflow_filter),
            "sort": _normalize_action_sort(sort),
            "total_items": len(items),
            "visible_items": min(len(sorted_items), safe_limit),
        }

    def session_library(self, *, sort: str = "newest", filter_status: str = "all") -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            rows = [dict(row) for row in fetch_session_library_rows(connection)]
        sessions = [self._hydrate_library_session(row) for row in rows]
        filtered = _filter_library_sessions(sessions, filter_status)
        sorted_sessions = _sort_library_sessions(filtered, sort)
        return {
            "sessions": sorted_sessions,
            "sort": _normalize_library_sort(sort),
            "filter": _normalize_library_filter(filter_status),
            "total_sessions": len(sessions),
            "visible_sessions": len(sorted_sessions),
        }

    def search_workspace(self, query: str, limit: int = 120, scope: str = "all") -> dict[str, object]:
        bootstrap_database(self.config)
        search_scopes = _search_scopes_for_filter(scope)
        with connection_context(self.config.database_path) as connection:
            rows = [
                dict(row)
                for row in search_capture_content(
                    connection,
                    query=query,
                    scopes=search_scopes,
                    limit=limit,
                )
            ]
        grouped: dict[str, dict[str, object]] = {}
        seen_matches: set[tuple[str, str, str]] = set()
        for row in rows:
            capture_id = str(row["capture_id"])
            content = str(row.get("content") or "")
            normalized_content = _normalize_search_text(content)
            if not normalized_content:
                continue
            dedupe_key = (capture_id, str(row.get("item_type")), normalized_content)
            if dedupe_key in seen_matches:
                continue
            seen_matches.add(dedupe_key)
            group = grouped.setdefault(
                capture_id,
                {
                    "capture_id": capture_id,
                    "display_name": row.get("session_display_name") or capture_id,
                    "lifecycle_state": row.get("lifecycle_state"),
                    "match_count": 0,
                    "matches": [],
                },
            )
            matches = group["matches"]
            if isinstance(matches, list) and len(matches) >= 5:
                continue
            group["matches"].append(
                {
                    "item_type": row.get("item_type"),
                    "field_name": _display_search_field(row.get("field_name"), row.get("item_type")),
                    "snippet": _build_snippet(content, query),
                    "rank_weight": row.get("rank_weight"),
                }
            )
            group["match_count"] = int(group["match_count"]) + 1
        sessions = list(grouped.values())
        return {
            "query": query,
            "scope": _normalize_search_scope(scope),
            "total_matches": sum(int(group["match_count"]) for group in sessions),
            "raw_matches": len(rows),
            "sessions": sessions,
        }

    def update_action_workflow_state(
        self,
        *,
        item_type: str,
        item_id: int,
        workflow_status: str,
    ) -> dict[str, object]:
        if workflow_status not in {"open", "done", "dismissed", "carried_forward"}:
            raise ValueError(f"Unsupported workflow status: {workflow_status}")
        if item_type not in {"action", "follow_up"}:
            raise ValueError("Only action and follow_up items support workflow updates.")
        reviewed_at = _utc_iso()
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = update_workspace_item_status(
                connection,
                item_type=item_type,
                item_id=item_id,
                workflow_status=workflow_status,
                reviewed_at=reviewed_at,
            )
            connection.commit()
        if row is None:
            raise ValueError(f"No {item_type} found with id {item_id}.")
        return _hydrate_workspace_item(dict(row))


    def update_action_details(
        self,
        *,
        item_type: str,
        item_id: int,
        due_at: str | None = None,
        notes: str | None = None,
    ) -> dict[str, object]:
        if item_type not in {"action", "follow_up"}:
            raise ValueError("Only action and follow_up items support details updates.")
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = update_workspace_item_details(
                connection,
                item_type=item_type,
                item_id=item_id,
                due_at=_clean_text(due_at),
                notes=_clean_text(notes),
                reviewed_at=_utc_iso(),
            )
            connection.commit()
        if row is None:
            raise ValueError(f"No {item_type} found with id {item_id}.")
        return _hydrate_workspace_item(dict(row))

    def finalise_session(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            self._assert_transition(str(row["status"]), "final")
            now = _utc_iso()
            update_meeting_fields(
                connection,
                capture_id,
                status="final",
                reviewed_at=row.get("reviewed_at") or now,
                updated_at=now,
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        return self._hydrate_session(dict(next_row))

    def memory_view(self, item_type: str, limit: int = 200) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            rows = [dict(row) for row in fetch_cross_session_action_items(connection, limit=limit)]
        filtered = [
            item for item in (_hydrate_workspace_item(row) for row in rows)
            if (
                item_type == "decisions" and item["item_type"] == "decision"
            ) or (
                item_type == "blockers_risks" and item["item_type"] == "blocker_risk"
            ) or (
                item_type == "open_questions" and item["item_type"] == "open_question"
            )
        ]
        return {"item_type": item_type, "items": filtered}

    def create_session(self, display_name: str | None = None) -> dict[str, object]:
        bootstrap_database(self.config)
        capture_id = f"capture-{uuid4().hex[:8]}"
        now = _utc_iso()
        title = _clean_text(display_name) or f"New Recording {now[:16].replace('T', ' ')}"
        with connection_context(self.config.database_path) as connection:
            insert_meeting(
                connection,
                MeetingRecord(
                    id=None,
                    external_id=f"capture:{capture_id}",
                    title=title,
                    status="draft",
                    started_at=now,
                    session_type="ad_hoc",
                    source_type="ad_hoc",
                    capture_id=capture_id,
                    created_at=now,
                    updated_at=now,
                    manual_title=bool(_clean_text(display_name)),
                    keep_source_audio=True,
                ),
            )
            connection.commit()
            row = fetch_meeting_by_capture_id(connection, capture_id)
        assert row is not None
        return self._hydrate_session(dict(row))

    def create_planned_session(
        self,
        *,
        display_name: str,
        planned_start_at: str | None = None,
        planning_notes: str | None = None,
    ) -> dict[str, object]:
        cleaned_title = _clean_text(display_name)
        if not cleaned_title:
            raise ValueError("Display name is required.")
        bootstrap_database(self.config)
        capture_id = f"capture-{uuid4().hex[:8]}"
        now = _utc_iso()
        with connection_context(self.config.database_path) as connection:
            insert_meeting(
                connection,
                MeetingRecord(
                    id=None,
                    external_id=f"capture:{capture_id}",
                    title=cleaned_title,
                    status="draft",
                    started_at=now,
                    session_type="planned",
                    source_type="planned",
                    planned_start_at=_clean_text(planned_start_at),
                    planning_notes=_clean_text(planning_notes),
                    capture_id=capture_id,
                    created_at=now,
                    updated_at=now,
                    manual_title=True,
                    keep_source_audio=True,
                ),
            )
            connection.commit()
            row = fetch_meeting_by_capture_id(connection, capture_id)
        assert row is not None
        return self._hydrate_session(dict(row))

    def list_upcoming_sessions(self, limit: int = 20) -> dict[str, object]:
        planned = self.list_planned_sessions(limit=limit).get("sessions", [])
        integration = self.microsoft_integration
        calendar_status = {
            "available": False,
            "provider": None,
            "message": "Live calendar integration is unavailable; manual planning remains available.",
        }
        imported: list[dict[str, object]] = []
        if integration is not None:
            result = integration.list_upcoming_meetings(limit=limit)
            calendar_status = {
                "available": bool(result.available),
                "provider": result.provider,
                "message": result.message,
            }
            imported = [self._meeting_to_upcoming_entry(item) for item in result.meetings]
        upcoming = planned + imported
        upcoming.sort(key=lambda row: str(row.get("planned_start_at") or row.get("created_at") or ""))
        safe_limit = max(1, min(int(limit), 100))
        return {"sessions": upcoming[:safe_limit], "calendar_status": calendar_status}

    def create_session_from_upcoming(self, meeting_context: dict[str, object]) -> dict[str, object]:
        imported_title = _clean_text(str(meeting_context.get("title") or ""))
        if not imported_title:
            raise ValueError("Upcoming meeting title is required.")
        planned_start_at = _clean_text(str(meeting_context.get("planned_start_at") or ""))
        external_meeting_id = _clean_text(str(meeting_context.get("external_meeting_id") or ""))
        metadata_json = meeting_context.get("imported_metadata_json")
        bootstrap_database(self.config)
        capture_id = f"capture-{uuid4().hex[:8]}"
        now = _utc_iso()
        with connection_context(self.config.database_path) as connection:
            insert_meeting(
                connection,
                MeetingRecord(
                    id=None,
                    external_id=f"capture:{capture_id}",
                    title=imported_title,
                    status="draft",
                    started_at=now,
                    session_type="planned",
                    source_type="calendar_imported",
                    planned_start_at=planned_start_at,
                    external_meeting_id=external_meeting_id,
                    imported_title=imported_title,
                    imported_metadata_json=str(metadata_json) if metadata_json else None,
                    capture_id=capture_id,
                    created_at=now,
                    updated_at=now,
                    manual_title=False,
                    keep_source_audio=True,
                ),
            )
            connection.commit()
            row = fetch_meeting_by_capture_id(connection, capture_id)
        assert row is not None
        return self._hydrate_session(dict(row))

    def list_planned_sessions(self, limit: int = 20) -> dict[str, object]:
        payload = self.session_library(sort="newest", filter_status="all")
        planned = [row for row in payload["sessions"] if row.get("session_type") == "planned" and row.get("lifecycle_state") in {"draft", "paused"}]
        planned.sort(key=lambda row: str(row.get("planned_start_at") or row.get("created_at") or ""), reverse=False)
        safe_limit = max(1, min(int(limit), 100))
        return {"sessions": planned[:safe_limit]}

    def get_session(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = fetch_meeting_by_capture_id(connection, capture_id)
        if row is None:
            raise ValueError(f"No session found for capture '{capture_id}'.")
        return self._hydrate_session(dict(row))

    def session_briefing(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            current = dict(row)
            meetings = [dict(item) for item in fetch_recent_meetings(connection, limit=300)]
            workspace = [_hydrate_workspace_item(dict(item)) for item in fetch_cross_session_action_items(connection, limit=1000)]

        related_ids = _related_capture_ids(current, meetings)
        related_ids.update(_carry_source_related_ids(related_ids, workspace))
        ordered_related_ids = _ordered_related_capture_ids(current, meetings, related_ids)
        prior_related_ids = [item for item in ordered_related_ids if item != capture_id]
        related_workspace = [
            item
            for item in workspace
            if str(item.get("capture_id")) in related_ids and str(item.get("capture_id")) != capture_id
        ]
        open_actions = _sort_briefing_items([
            item
            for item in related_workspace
            if item.get("item_type") == "action" and item.get("workflow_state") == "open"
        ])[:6]
        carried = _sort_briefing_items([
            item
            for item in related_workspace
            if item.get("item_type") in {"action", "follow_up"} and item.get("workflow_state") == "carried_forward"
        ])[:6]
        blockers = _review_preferred_briefing_items([
            item
            for item in related_workspace
            if item.get("item_type") == "blocker_risk" and item.get("workflow_state") in {"open", "carried_forward"}
        ])[:5]
        questions = _review_preferred_briefing_items([
            item
            for item in related_workspace
            if item.get("item_type") == "open_question" and item.get("workflow_state") in {"open", "carried_forward"}
        ])[:5]
        decisions = _review_preferred_briefing_items([
            item for item in related_workspace if item.get("item_type") == "decision"
        ])[:5]
        executive = self._prior_executive_summary(prior_related_ids)
        return {
            "capture_id": capture_id,
            "display_name": current.get("title") or capture_id,
            "related_session_ids": prior_related_ids,
            "briefing": {
                "open_actions": open_actions,
                "carried_forward_items": carried,
                "recent_decisions": decisions,
                "active_blockers_risks": blockers,
                "open_questions": questions,
                "prior_executive_summary": executive,
            },
        }

    def _prior_executive_summary(self, related_capture_ids: list[str]) -> str | None:
        candidates: list[tuple[int, int, str]] = []
        for index, related_capture_id in enumerate(related_capture_ids[:12]):
            try:
                payload = self.export_service.build_review_payload(related_capture_id, export_mode="final_notes")
            except Exception as error:  # pragma: no cover - defensive only; briefing should never block capture.
                self.logger.warning("Could not build briefing summary for %s: %s", related_capture_id, error)
                continue
            metadata = payload.get("metadata", {})
            content_state = str(metadata.get("content_state") or "generated") if isinstance(metadata, dict) else "generated"
            state_rank = 0 if content_state in {"final", "reviewed", "exported"} else 1
            for summary in payload.get("summaries", []):
                if str(summary.get("summary_type")) != "executive":
                    continue
                if summary.get("quality_status") == "low_confidence":
                    continue
                content = str(summary.get("content") or "").strip()
                if content:
                    candidates.append((state_rank, index, content[:420]))
                    break
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

    def update_session_display_name(self, capture_id: str, display_name: str) -> dict[str, object]:
        cleaned = _clean_text(display_name)
        if not cleaned:
            raise ValueError("Display name is required.")
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            self._require_session(connection, capture_id)
            update_meeting_fields(
                connection,
                capture_id,
                title=cleaned,
                manual_title=1,
                updated_at=_utc_iso(),
            )
            connection.commit()
            row = fetch_meeting_by_capture_id(connection, capture_id)
        assert row is not None
        return self._hydrate_session(dict(row))

    def start_session(
        self,
        capture_id: str,
        *,
        include_loopback: bool = True,
        include_microphone: bool = True,
    ) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            self._assert_transition(str(row["status"]), "recording")
            now = _utc_iso()
            state = self.audio_capture.start_capture(
                include_loopback=include_loopback,
                include_microphone=include_microphone,
                chunk_seconds=self.config.audio_chunk_seconds,
                sample_rate=self.config.audio_sample_rate,
                channels=self.config.audio_channels,
                capture_id=capture_id,
            )
            capture_status = str(state.get("status") or "")
            if capture_status != "running":
                last_error = str(
                    state.get("last_error")
                    or state.get("message")
                    or f"Audio capture did not remain active; startup ended with status '{capture_status or 'unknown'}'."
                )
                update_meeting_fields(
                    connection,
                    capture_id,
                    updated_at=now,
                    last_error=last_error,
                )
                connection.commit()
                raise RuntimeError(last_error)
            update_meeting_fields(
                connection,
                capture_id,
                status="recording",
                started_at=row["started_at"] if str(row["status"]) != "draft" else now,
                updated_at=now,
                last_recording_started_at=now,
                last_error=None,
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        session = self._hydrate_session(dict(next_row))
        session["active_capture"] = state
        return session

    def pause_session(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        now = _utc_now()
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            self._assert_transition(str(row["status"]), "paused")
        active_capture = self.audio_capture.status()
        if active_capture.get("capture_id") != capture_id:
            raise ValueError(f"Active audio capture does not match session '{capture_id}'.")
        stopped_state = self.audio_capture.stop_capture(
            timeout_seconds=max(10.0, float(self.config.audio_chunk_seconds) + 5.0)
        )
        stopped_status = str(stopped_state.get("status") or "")
        if stopped_status not in {"stopped", "failed"}:
            raise RuntimeError(
                "Audio capture is still stopping. Wait for the current chunk to finish before resuming."
            )
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            update_meeting_fields(
                connection,
                capture_id,
                status="paused",
                updated_at=now.isoformat(),
                last_recording_started_at=None,
                recorded_seconds=_accumulated_recorded_seconds(dict(row), now),
                last_error=stopped_state.get("last_error"),
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        session = self._hydrate_session(dict(next_row))
        session["active_capture"] = stopped_state
        return session

    def resume_session(
        self,
        capture_id: str,
        *,
        include_loopback: bool = True,
        include_microphone: bool = True,
    ) -> dict[str, object]:
        return self.start_session(
            capture_id,
            include_loopback=include_loopback,
            include_microphone=include_microphone,
        )

    def stop_session(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        capture_state = self.audio_capture.status()
        if capture_state.get("capture_id") == capture_id and capture_state.get("status") in {"starting", "running"}:
            capture_state = self.audio_capture.stop_capture()

        now = _utc_now()
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            current_status = str(row["status"])
            if current_status == "recording":
                self._assert_transition(current_status, "processing")
            elif current_status != "paused":
                raise ValueError(f"Cannot stop session from state '{current_status}'.")
            update_meeting_fields(
                connection,
                capture_id,
                status="processing",
                updated_at=now.isoformat(),
                ended_at=now.isoformat(),
                last_recording_started_at=None,
                recorded_seconds=_accumulated_recorded_seconds(dict(row), now),
                last_error=None,
            )
            connection.commit()

        try:
            self._process_capture(capture_id)
            next_status = "review_ready"
            error = None
        except Exception as exc:
            self.logger.exception("Processing failed for %s", capture_id)
            next_status = "processing_failed"
            error = str(exc)

        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            providers = self.export_service.build_review_payload(capture_id)["metadata"]["providers"]
            update_meeting_fields(
                connection,
                capture_id,
                status=next_status,
                updated_at=_utc_iso(),
                last_processed_at=_utc_iso(),
                last_error=error,
                latest_provider_name=providers[0] if providers else row["latest_provider_name"],
                raw_audio_expires_at=self._raw_audio_expiry_for_session(dict(row)),
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        session = self._hydrate_session(dict(next_row))
        session["active_capture"] = capture_state if capture_state.get("capture_id") == capture_id else None
        return session

    def export_session(self, capture_id: str, export_format: str, export_mode: str | None = None) -> Path:
        output_path = self.export_service.export_capture(capture_id, export_format, export_mode=export_mode)
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            next_status = "exported" if str(row["status"]) != "archived" else str(row["status"])
            update_meeting_fields(
                connection,
                capture_id,
                status=next_status,
                exported_at=_utc_iso(),
                updated_at=_utc_iso(),
            )
            connection.commit()
        return output_path

    def update_retention_settings(
        self,
        *,
        raw_audio_retention_days: int,
        delete_temp_processing_files: bool,
    ) -> dict[str, object]:
        now = _utc_iso()
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            upsert_app_setting(connection, "raw_audio_retention_days", int(raw_audio_retention_days), now)
            upsert_app_setting(
                connection,
                "delete_temp_processing_files",
                bool(delete_temp_processing_files),
                now,
            )
            connection.commit()
            settings = self._settings_with_defaults(fetch_app_settings(connection))
        return settings

    def update_keep_source_audio(self, capture_id: str, keep_source_audio: bool) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            update_meeting_fields(
                connection,
                capture_id,
                keep_source_audio=keep_source_audio,
                raw_audio_expires_at=None if keep_source_audio else self._raw_audio_expiry_for_session(dict(row)),
                updated_at=_utc_iso(),
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        return self._hydrate_session(dict(next_row))

    def delete_source_audio(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            if str(row["status"]) in {"recording", "processing"}:
                raise ValueError("Cannot delete source audio while a session is recording or processing.")
            audio_dir = self.config.audio_output_dir / capture_id
            if audio_dir.exists():
                shutil.rmtree(audio_dir)
            update_meeting_fields(
                connection,
                capture_id,
                keep_source_audio=0,
                source_audio_deleted_at=_utc_iso(),
                raw_audio_expires_at=None,
                updated_at=_utc_iso(),
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        return self._hydrate_session(dict(next_row))

    def archive_session(self, capture_id: str) -> dict[str, object]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = self._require_session(connection, capture_id)
            self._assert_transition(str(row["status"]), "archived")
            update_meeting_fields(
                connection,
                capture_id,
                status="archived",
                archived_at=_utc_iso(),
                updated_at=_utc_iso(),
            )
            connection.commit()
            next_row = fetch_meeting_by_capture_id(connection, capture_id)
        assert next_row is not None
        return self._hydrate_session(dict(next_row))

    def cleanup_retention(self) -> dict[str, object]:
        bootstrap_database(self.config)
        now = _utc_now()
        deleted_audio = 0
        deleted_temp_files = 0
        with connection_context(self.config.database_path) as connection:
            settings = self._settings_with_defaults(fetch_app_settings(connection))
            rows = [dict(row) for row in fetch_recent_meetings(connection, limit=500)]
            for row in rows:
                expires_at = row.get("raw_audio_expires_at")
                if (
                    row.get("keep_source_audio")
                    or row.get("source_audio_deleted_at")
                    or not expires_at
                    or str(row.get("status")) in {"recording", "processing"}
                ):
                    continue
                if datetime.fromisoformat(str(expires_at)) > now:
                    continue
                audio_dir = self.config.audio_output_dir / str(row["capture_id"])
                if audio_dir.exists():
                    shutil.rmtree(audio_dir)
                update_meeting_fields(
                    connection,
                    str(row["capture_id"]),
                    source_audio_deleted_at=now.isoformat(),
                    raw_audio_expires_at=None,
                    updated_at=now.isoformat(),
                )
                deleted_audio += 1
            connection.commit()

        if settings["delete_temp_processing_files"]:
            for stop_path in self.config.temp_output_dir.glob("capture-*.stop"):
                stop_path.unlink(missing_ok=True)
                deleted_temp_files += 1

        return {
            "deleted_audio_sessions": deleted_audio,
            "deleted_temp_files": deleted_temp_files,
            "ran_at": now.isoformat(),
        }

    def _process_capture(self, capture_id: str) -> None:
        self.transcription_engine.transcribe_capture(capture_id)
        self.diarization_engine.diarize_capture(capture_id)
        self.summarizer.generate_summaries(capture_id)
        self.action_extractor.extract_capture(capture_id)

    def _require_session(self, connection, capture_id: str):
        row = fetch_meeting_by_capture_id(connection, capture_id)
        if row is None:
            raise ValueError(f"No session found for capture '{capture_id}'.")
        return row

    def _assert_transition(self, current_status: str, next_status: str) -> None:
        allowed = self.allowed_transitions.get(current_status, set())
        if next_status not in allowed:
            raise ValueError(f"Cannot move session from '{current_status}' to '{next_status}'.")

    def _settings_with_defaults(self, stored: dict[str, object]) -> dict[str, object]:
        return {
            "raw_audio_retention_days": int(
                stored.get("raw_audio_retention_days", self.config.raw_audio_retention_days)
            ),
            "delete_temp_processing_files": bool(
                stored.get("delete_temp_processing_files", self.config.delete_temp_processing_files)
            ),
        }

    def _raw_audio_expiry_for_session(self, row: dict[str, object]) -> str | None:
        if row.get("keep_source_audio"):
            return None
        settings = self.dashboard_payload()["settings"]
        ended_at = str(row.get("ended_at") or row.get("updated_at") or _utc_iso())
        return (
            datetime.fromisoformat(ended_at)
            + timedelta(days=int(settings["raw_audio_retention_days"]))
        ).replace(microsecond=0).isoformat()

    def _hydrate_session(self, row: dict[str, object]) -> dict[str, object]:
        capture_state = self.audio_capture.status()
        active_capture = capture_state if capture_state.get("capture_id") == row.get("capture_id") else None
        return {
            "id": row["id"],
            "capture_id": row["capture_id"],
            "display_name": row["title"],
            "session_type": row.get("session_type") or "ad_hoc",
            "source_type": row.get("source_type") or row.get("session_type") or "ad_hoc",
            "planned_start_at": row.get("planned_start_at"),
            "planning_notes": row.get("planning_notes"),
            "external_meeting_id": row.get("external_meeting_id"),
            "imported_title": row.get("imported_title"),
            "imported_metadata_json": row.get("imported_metadata_json"),
            "lifecycle_state": row["status"],
            "created_at": row.get("created_at") or row["started_at"],
            "updated_at": row.get("updated_at") or row["started_at"],
            "started_at": row["started_at"],
            "ended_at": row.get("ended_at"),
            "recorded_seconds": int(row.get("recorded_seconds") or 0),
            "reviewed_items_exist": bool(row.get("has_reviewed_items")),
            "latest_provider_name": row.get("latest_provider_name"),
            "latest_model_name": row.get("latest_model_name"),
            "keep_source_audio": bool(row.get("keep_source_audio")),
            "source_audio_deleted_at": row.get("source_audio_deleted_at"),
            "raw_audio_expires_at": row.get("raw_audio_expires_at"),
            "reviewed_at": row.get("reviewed_at"),
            "exported_at": row.get("exported_at"),
            "archived_at": row.get("archived_at"),
            "last_processed_at": row.get("last_processed_at"),
            "last_error": row.get("last_error"),
            "audio_present": (self.config.audio_output_dir / str(row["capture_id"])).exists(),
            "active_capture": active_capture,
        }

    def _meeting_to_upcoming_entry(self, meeting: dict[str, str]) -> dict[str, object]:
        return {
            "capture_id": "",
            "display_name": meeting["title"],
            "session_type": "planned",
            "source_type": "calendar_imported",
            "planned_start_at": meeting.get("planned_start_at"),
            "external_meeting_id": meeting.get("external_meeting_id"),
            "imported_title": meeting.get("title"),
            "imported_metadata_json": meeting.get("imported_metadata_json"),
            "lifecycle_state": "draft",
            "is_upcoming_placeholder": True,
        }

    def _hydrate_library_session(self, row: dict[str, object]) -> dict[str, object]:
        payload = self._hydrate_session(row)
        payload["providers"] = _split_csv_fields(
            row.get("summary_providers"),
            row.get("action_providers"),
            row.get("decision_providers"),
            row.get("follow_up_providers"),
        )
        payload["models"] = _split_csv_fields(
            row.get("summary_models"),
            row.get("action_models"),
            row.get("decision_models"),
            row.get("follow_up_models"),
        )
        return payload


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _accumulated_recorded_seconds(row: dict[str, object], now: datetime) -> int:
    base = int(row.get("recorded_seconds") or 0)
    started_at = row.get("last_recording_started_at")
    if not started_at:
        return base
    return base + max(0, int((now - datetime.fromisoformat(str(started_at))).total_seconds()))


def _hydrate_workspace_item(row: dict[str, object]) -> dict[str, object]:
    reviewed_description = _clean_text(row.get("reviewed_description"))
    reviewed_owner_name = _clean_text(row.get("reviewed_owner_name"))
    last_updated_at = (
        row.get("reviewed_at")
        or row.get("generated_at")
        or row.get("source_updated_at")
    )
    return {
        "id": row["id"],
        "item_type": row["item_type"],
        "capture_id": row["capture_id"],
        "source_display_name": row.get("source_display_name") or row["capture_id"],
        "source_lifecycle_state": row.get("source_lifecycle_state"),
        "source_updated_at": row.get("source_updated_at"),
        "description": row.get("description") or "",
        "effective_description": reviewed_description or row.get("description") or "",
        "owner_name": row.get("owner_name"),
        "effective_owner_name": reviewed_owner_name or row.get("owner_name"),
        "workflow_state": _compact_workflow_state(row.get("workflow_state")),
        "review_status": row.get("review_status") or "generated",
        "due_at": row.get("due_at"),
        "notes": row.get("notes"),
        "carry_source_capture_id": row.get("carry_source_capture_id"),
        "carry_count": int(row.get("carry_count") or 0),
        "reviewed_at": row.get("reviewed_at"),
        "last_updated_at": last_updated_at,
        "evidence_snippet": row.get("evidence_snippet"),
        "start_offset_seconds": row.get("start_offset_seconds"),
        "end_offset_seconds": row.get("end_offset_seconds"),
        "provider_name": row.get("provider_name"),
        "model_name": row.get("model_name"),
        "generated_at": row.get("generated_at"),
    }


def _compact_workflow_state(value: object) -> str:
    state = str(value or "open").strip().casefold()
    if state in {"done", "closed", "complete", "completed"}:
        return "done"
    if state in {"dismissed", "ignore"}:
        return "dismissed"
    if state in {"carried", "carry", "carried_forward"}:
        return "carried_forward"
    if state in {"blocked", "risk"}:
        return "open"
    return "open"


def _normalize_action_filter(value: str | None) -> str:
    filter_value = str(value or "active").strip().casefold().replace("_", "-")
    aliases = {
        "all": "all",
        "active": "active",
        "open": "open",
        "open-only": "open",
        "done": "done",
        "complete": "done",
        "completed": "done",
        "carried": "carried-forward",
        "carry-forward": "carried-forward",
        "carried-forward": "carried-forward",
        "dismissed": "dismissed",
        "overdue": "overdue",
        "due-soon": "due-soon",
    }
    return aliases.get(filter_value, "active")


def _filter_action_workspace_items(
    items: list[dict[str, object]], workflow_filter: str
) -> list[dict[str, object]]:
    normalized = _normalize_action_filter(workflow_filter)
    if normalized == "all":
        return items
    if normalized == "active":
        return [item for item in items if item.get("workflow_state") in {"open", "carried_forward"}]
    if normalized == "carried-forward":
        return [item for item in items if item.get("workflow_state") == "carried_forward"]
    if normalized == "overdue":
        now_iso = _utc_now().isoformat()
        return [item for item in items if item.get("due_at") and str(item["due_at"]) < now_iso and item.get("workflow_state") in {"open", "carried_forward"}]
    if normalized == "due-soon":
        now = _utc_now()
        soon = (now + timedelta(days=3)).isoformat()
        now_iso = now.isoformat()
        return [item for item in items if item.get("due_at") and now_iso <= str(item["due_at"]) <= soon and item.get("workflow_state") in {"open", "carried_forward"}]
    return [item for item in items if item.get("workflow_state") == normalized]


def _normalize_action_sort(value: str | None) -> str:
    sort = str(value or "recent").strip().casefold().replace("_", "-")
    if sort in {"oldest", "owner", "session"}:
        return sort
    return "recent"


def _sort_action_workspace_items(
    items: list[dict[str, object]], sort: str
) -> list[dict[str, object]]:
    normalized = _normalize_action_sort(sort)
    if normalized == "oldest":
        return sorted(
            items,
            key=lambda item: (
                str(item.get("last_updated_at") or ""),
                str(item.get("capture_id") or ""),
                int(item.get("id") or 0),
            ),
        )
    if normalized == "owner":
        return sorted(
            items,
            key=lambda item: (
                str(item.get("effective_owner_name") or "Unknown").casefold(),
                str(item.get("last_updated_at") or ""),
                int(item.get("id") or 0),
            ),
        )
    if normalized == "session":
        return sorted(
            items,
            key=lambda item: (
                str(item.get("source_display_name") or item.get("capture_id") or "").casefold(),
                str(item.get("last_updated_at") or ""),
                int(item.get("id") or 0),
            ),
        )
    return sorted(
        items,
        key=lambda item: (
            str(item.get("last_updated_at") or ""),
            str(item.get("capture_id") or ""),
            int(item.get("id") or 0),
        ),
        reverse=True,
    )


def _sort_briefing_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    recent_first = sorted(
        items,
        key=lambda item: (
            str(item.get("last_updated_at") or ""),
            str(item.get("capture_id") or ""),
            int(item.get("id") or 0),
        ),
        reverse=True,
    )
    return sorted(recent_first, key=_briefing_quality_rank)


def _review_preferred_briefing_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    sorted_items = _sort_briefing_items(items)
    reviewed = [item for item in sorted_items if item.get("review_status") in {"accepted", "edited"}]
    return reviewed or sorted_items


def _briefing_quality_rank(item: dict[str, object]) -> int:
    if item.get("review_status") in {"accepted", "edited"}:
        return 0
    if item.get("source_lifecycle_state") in {"final", "reviewed", "exported"}:
        return 1
    return 2


def _normalize_library_sort(value: str | None) -> str:
    sort = str(value or "newest").strip().casefold().replace("_", "-")
    if sort in {"oldest", "oldest-first"}:
        return "oldest"
    return "newest"


def _normalize_library_filter(value: str | None) -> str:
    filter_status = str(value or "all").strip().casefold().replace("_", "-")
    allowed = {"all", "review-ready", "finalised", "exported", "needs-attention"}
    return filter_status if filter_status in allowed else "all"


def _filter_library_sessions(
    sessions: list[dict[str, object]], filter_status: str
) -> list[dict[str, object]]:
    normalized = _normalize_library_filter(filter_status)
    if normalized == "all":
        return sessions
    if normalized == "review-ready":
        return [
            session for session in sessions
            if session.get("lifecycle_state") in {"review_ready", "reviewed"}
        ]
    if normalized == "finalised":
        return [
            session for session in sessions
            if session.get("lifecycle_state") in {"final", "exported"}
        ]
    if normalized == "exported":
        return [
            session for session in sessions
            if session.get("lifecycle_state") == "exported" or bool(session.get("exported_at"))
        ]
    if normalized == "needs-attention":
        return [
            session for session in sessions
            if session.get("lifecycle_state") == "processing_failed" or bool(session.get("last_error"))
        ]
    return sessions


def _sort_library_sessions(
    sessions: list[dict[str, object]], sort: str
) -> list[dict[str, object]]:
    reverse = _normalize_library_sort(sort) == "newest"
    return sorted(
        sessions,
        key=lambda session: (
            str(session.get("updated_at") or session.get("created_at") or ""),
            str(session.get("capture_id") or ""),
        ),
        reverse=reverse,
    )


def _normalize_search_scope(value: str | None) -> str:
    scope = str(value or "all").strip().casefold().replace("_", "-")
    allowed = {"all", "sessions", "summaries", "actions", "decisions", "blockers-risks", "open-questions"}
    return scope if scope in allowed else "all"


def _search_scopes_for_filter(value: str | None) -> list[str] | None:
    scope = _normalize_search_scope(value)
    if scope == "sessions":
        return ["session"]
    if scope == "summaries":
        return ["summary"]
    if scope == "actions":
        return ["action", "follow_up"]
    if scope == "decisions":
        return ["decision"]
    if scope == "blockers-risks":
        return ["blocker_risk"]
    if scope == "open-questions":
        return ["open_question"]
    return None


def _normalize_search_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _related_capture_ids(current: dict[str, object], meetings: list[dict[str, object]]) -> set[str]:
    current_id = str(current.get("capture_id") or "")
    current_titles = _meeting_title_keys(current)
    current_external = str(current.get("external_meeting_id") or "").strip()
    related: set[str] = {current_id}
    for meeting in meetings:
        capture_id = str(meeting.get("capture_id") or "")
        if not capture_id:
            continue
        titles = _meeting_title_keys(meeting)
        external_id = str(meeting.get("external_meeting_id") or "").strip()
        if current_external and external_id and external_id == current_external:
            related.add(capture_id)
            continue
        if current_titles and titles and current_titles.intersection(titles):
            related.add(capture_id)
    return related


def _meeting_title_keys(meeting: dict[str, object]) -> set[str]:
    return {
        normalized
        for normalized in (
            _normalize_search_text(str(meeting.get("title") or "")),
            _normalize_search_text(str(meeting.get("imported_title") or "")),
        )
        if normalized
    }


def _carry_source_related_ids(related_ids: set[str], workspace: list[dict[str, object]]) -> set[str]:
    expanded: set[str] = set()
    for item in workspace:
        capture_id = str(item.get("capture_id") or "")
        carry_source_capture_id = str(item.get("carry_source_capture_id") or "")
        if not carry_source_capture_id:
            continue
        if capture_id in related_ids:
            expanded.add(carry_source_capture_id)
        if carry_source_capture_id in related_ids and capture_id:
            expanded.add(capture_id)
    return expanded


def _ordered_related_capture_ids(
    current: dict[str, object],
    meetings: list[dict[str, object]],
    related_ids: set[str],
) -> list[str]:
    current_id = str(current.get("capture_id") or "")
    ordered: list[str] = []
    for meeting in meetings:
        capture_id = str(meeting.get("capture_id") or "")
        if capture_id and capture_id in related_ids and capture_id not in ordered:
            ordered.append(capture_id)
    if current_id and current_id in related_ids and current_id not in ordered:
        ordered.insert(0, current_id)
    for capture_id in sorted(related_ids):
        if capture_id and capture_id not in ordered:
            ordered.append(capture_id)
    return ordered


def _display_search_field(field_name: object, item_type: object) -> str:
    field = str(field_name or item_type or "match").replace("_", " ")
    if field.endswith(" evidence"):
        field = f"{field[:-9]} evidence"
    return field


def _split_csv_fields(*values: object) -> list[str]:
    items: set[str] = set()
    for value in values:
        if value is None:
            continue
        for part in str(value).split(","):
            text = part.strip()
            if text:
                items.add(text)
    return sorted(items)


def _build_snippet(content: str, query: str, size: int = 110) -> str:
    cleaned = " ".join(content.split())
    if not cleaned:
        return ""
    lowered = cleaned.casefold()
    marker = query.strip().casefold()
    index = lowered.find(marker) if marker else 0
    if index < 0:
        return cleaned[:size]
    start = max(0, index - (size // 2))
    end = min(len(cleaned), start + size)
    snippet = cleaned[start:end]
    if start > 0:
        snippet = f"…{snippet}"
    if end < len(cleaned):
        snippet = f"{snippet}…"
    return snippet
