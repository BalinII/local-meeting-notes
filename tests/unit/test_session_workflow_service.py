from __future__ import annotations

import sqlite3
from pathlib import Path

from local_meeting_notes.config import load_config
from local_meeting_notes.models import ActionRecord, DecisionRecord, FollowUpRecord, SummaryRecord, TranscriptSegmentRecord
from local_meeting_notes.session_workflow.service import SessionWorkflowService
from local_meeting_notes.storage.database import bootstrap_database, connection_context
from local_meeting_notes.storage.repository import (
    insert_action,
    insert_decision,
    insert_follow_up,
    insert_summary,
    insert_transcript_segment,
    update_meeting_fields,
)


class FakeAudioCaptureService:
    def __init__(self) -> None:
        self.current: dict[str, object] = {"status": "idle"}
        self.started_capture_ids: list[str] = []

    def start_capture(
        self,
        *,
        include_loopback: bool,
        include_microphone: bool,
        chunk_seconds: int,
        sample_rate: int,
        channels: int,
        capture_id: str | None = None,
    ) -> dict[str, object]:
        assert capture_id is not None
        self.started_capture_ids.append(capture_id)
        self.current = {
            "capture_id": capture_id,
            "status": "running",
            "include_loopback": include_loopback,
            "include_microphone": include_microphone,
            "started_at": "2026-04-25T00:00:00+00:00",
        }
        return self.current

    def stop_capture(self, timeout_seconds: float = 10.0) -> dict[str, object]:
        if self.current.get("capture_id"):
            self.current = {
                "capture_id": self.current["capture_id"],
                "status": "stopped",
            }
        else:
            self.current = {"status": "idle"}
        return self.current

    def status(self) -> dict[str, object]:
        return self.current


class FakeSlowStoppingAudioCaptureService(FakeAudioCaptureService):
    def stop_capture(self, timeout_seconds: float = 10.0) -> dict[str, object]:
        return {
            "capture_id": self.current.get("capture_id"),
            "status": "stopping",
        }


class FakeNoopService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def transcribe_capture(self, capture_id: str) -> dict[str, object]:
        self.calls.append(f"transcribe:{capture_id}")
        return {"capture_id": capture_id}

    def diarize_capture(self, capture_id: str) -> dict[str, object]:
        self.calls.append(f"diarize:{capture_id}")
        return {"capture_id": capture_id}

    def generate_summaries(self, capture_id: str, provider_name: str | None = None) -> dict[str, object]:
        self.calls.append(f"summarize:{capture_id}")
        return {"capture_id": capture_id}

    def extract_capture(self, capture_id: str, provider_name: str | None = None) -> dict[str, object]:
        self.calls.append(f"extract:{capture_id}")
        return {"capture_id": capture_id}


class FakeExportService:
    def build_review_payload(self, capture_id: str) -> dict[str, object]:
        return {
            "capture_id": capture_id,
            "exported_at": "2026-04-25T00:00:00+00:00",
            "metadata": {
                "providers": ["local_llm"],
                "summary_count": 0,
                "action_count": 0,
                "decision_count": 0,
                "follow_up_count": 0,
            },
            "summaries": [],
            "actions": [],
            "decisions": [],
            "follow_ups": [],
            "blockers_risks": [],
            "open_questions": [],
        }

    def export_capture(self, capture_id: str, export_format: str) -> Path:
        return Path(f"{capture_id}.{export_format}")


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


def test_session_workflow_keeps_one_capture_id_across_resume(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    audio = FakeAudioCaptureService()
    transcription = FakeNoopService()
    diarization = FakeNoopService()
    summaries = FakeNoopService()
    actions = FakeNoopService()
    service = SessionWorkflowService(
        config,
        audio_capture=audio,
        transcription_engine=transcription,  # type: ignore[arg-type]
        diarization_engine=diarization,  # type: ignore[arg-type]
        summarizer=summaries,  # type: ignore[arg-type]
        action_extractor=actions,  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )

    created = service.create_session("Team Weekly")
    started = service.start_session(created["capture_id"])
    paused = service.pause_session(created["capture_id"])
    resumed = service.resume_session(created["capture_id"])
    stopped = service.stop_session(created["capture_id"])

    assert created["capture_id"] == started["capture_id"] == paused["capture_id"] == resumed["capture_id"] == stopped["capture_id"]
    assert audio.started_capture_ids == [created["capture_id"], created["capture_id"]]
    assert paused["lifecycle_state"] == "paused"
    assert resumed["lifecycle_state"] == "recording"
    assert stopped["lifecycle_state"] == "review_ready"
    assert transcription.calls == [f"transcribe:{created['capture_id']}"]
    assert diarization.calls == [f"diarize:{created['capture_id']}"]
    assert summaries.calls == [f"summarize:{created['capture_id']}"]
    assert actions.calls == [f"extract:{created['capture_id']}"]


def test_session_cleanup_deletes_expired_audio_only(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Cleanup Target")
    audio_dir = config.audio_output_dir / created["capture_id"]
    audio_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "000001_chunk.wav").write_text("stub", encoding="utf-8")
    with connection_context(config.database_path) as connection:
        update_meeting_fields(
            connection,
            created["capture_id"],
            keep_source_audio=0,
            raw_audio_expires_at="2000-01-01T00:00:00+00:00",
            updated_at="2026-04-25T00:00:00+00:00",
        )
        connection.commit()

    result = service.cleanup_retention()

    assert result["deleted_audio_sessions"] == 1
    assert not audio_dir.exists()


def test_pause_wrong_capture_does_not_stop_active_capture(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    audio = FakeAudioCaptureService()
    service = SessionWorkflowService(
        config,
        audio_capture=audio,  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    active = service.create_session("Active")
    stale = service.create_session("Stale")
    service.start_session(active["capture_id"])

    try:
        service.pause_session(stale["capture_id"])
    except ValueError as exc:
        assert "Cannot move session" in str(exc) or "Active audio capture" in str(exc)
    else:
        raise AssertionError("pause_session should reject a stale capture id")

    assert audio.current["status"] == "running"
    assert audio.current["capture_id"] == active["capture_id"]


def test_pause_waits_for_capture_to_stop_before_marking_session_paused(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    audio = FakeSlowStoppingAudioCaptureService()
    service = SessionWorkflowService(
        config,
        audio_capture=audio,  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Slow Pause")
    service.start_session(created["capture_id"])

    try:
        service.pause_session(created["capture_id"])
    except RuntimeError as exc:
        assert "still stopping" in str(exc)
    else:
        raise AssertionError("pause_session should not mark a session paused while audio is still stopping")

    assert service.get_session(created["capture_id"])["lifecycle_state"] == "recording"


def test_dashboard_payload_includes_source_traced_action_workspace(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Workspace Source")

    with connection_context(config.database_path) as connection:
        meeting_id = int(created["id"])
        insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=str(created["capture_id"]),
                description="Follow up on the export review pass.",
                owner_name="Unconfirmed speaker",
                status="open",
                evidence_snippet="Action item: follow up on export review.",
            ),
        )
        insert_follow_up(
            connection,
            FollowUpRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=str(created["capture_id"]),
                description="Extraction evidence may be weak.",
                follow_up_type="blocker_risk",
                owner_name="Unknown",
                status="blocked",
                evidence_snippet="Risk: weak evidence on extraction quality.",
            ),
        )
        connection.commit()

    payload = service.dashboard_payload()

    items = payload["action_items"]
    assert len(items) == 2
    assert {item["item_type"] for item in items} == {"action", "blocker_risk"}
    assert {item["capture_id"] for item in items} == {created["capture_id"]}
    assert {item["source_display_name"] for item in items} == {"Workspace Source"}
    assert {item["workflow_state"] for item in items} == {"open"}


def test_library_search_and_workflow_updates(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Roadmap Planning")
    with connection_context(config.database_path) as connection:
        meeting_id = int(created["id"])
        insert_transcript_segment(
            connection,
            TranscriptSegmentRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=str(created["capture_id"]),
                source_chunk_path="chunk.wav",
                transcription_status="completed",
                speaker_label="Ben",
                content="Ben said the meeting should stay local-first and review the decision.",
                start_offset_seconds=0,
                end_offset_seconds=8,
            ),
        )
        insert_summary(
            connection,
            SummaryRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=str(created["capture_id"]),
                title="Executive Summary",
                content="The meeting focused on local-first review and decision tracking.",
                summary_type="executive",
                evidence_snippet="Ben said the meeting should stay local-first.",
            ),
        )
        insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=str(created["capture_id"]),
                description="Carry roadmap tasks to next sprint planning.",
                owner_name="Unconfirmed speaker",
                status="open",
                evidence_snippet="Action: carry roadmap tasks.",
            ),
        )
        insert_decision(
            connection,
            DecisionRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=str(created["capture_id"]),
                description="Keep the meeting notes workflow local-first.",
                evidence_snippet="Decision: keep the workflow local-first.",
            ),
        )
        connection.commit()

    library = service.session_library()
    assert any(session["capture_id"] == created["capture_id"] for session in library["sessions"])

    search = service.search_workspace("roadmap")
    assert search["total_matches"] >= 1
    assert any(group["capture_id"] == created["capture_id"] for group in search["sessions"])
    for query in ("local-first", "Ben", "review", "decision", "meeting"):
        result = service.search_workspace(query)
        assert result["total_matches"] >= 1
        assert any(group["capture_id"] == created["capture_id"] for group in result["sessions"])

    item = service.dashboard_payload()["action_items"][0]
    updated = service.update_action_workflow_state(
        item_type="action",
        item_id=int(item["id"]),
        workflow_status="carried_forward",
    )
    assert updated["workflow_state"] == "carried_forward"

    refreshed = service.dashboard_payload()["action_items"][0]
    assert refreshed["workflow_state"] == "carried_forward"


def test_session_library_supports_pragmatic_sorting_and_filters(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    older = service.create_session("Older Review")
    newer = service.create_session("Newer Export")
    failed = service.create_session("Failed Capture")

    with connection_context(config.database_path) as connection:
        update_meeting_fields(
            connection,
            str(older["capture_id"]),
            status="review_ready",
            updated_at="2026-04-20T00:00:00+00:00",
        )
        update_meeting_fields(
            connection,
            str(newer["capture_id"]),
            status="exported",
            exported_at="2026-04-22T00:00:00+00:00",
            updated_at="2026-04-22T00:00:00+00:00",
        )
        update_meeting_fields(
            connection,
            str(failed["capture_id"]),
            status="processing_failed",
            last_error="Transcription failed",
            updated_at="2026-04-21T00:00:00+00:00",
        )
        connection.commit()

    newest = service.session_library(sort="newest")["sessions"]
    oldest = service.session_library(sort="oldest")["sessions"]

    assert [session["capture_id"] for session in newest] == [
        newer["capture_id"],
        failed["capture_id"],
        older["capture_id"],
    ]
    assert [session["capture_id"] for session in oldest] == [
        older["capture_id"],
        failed["capture_id"],
        newer["capture_id"],
    ]
    assert [session["capture_id"] for session in service.session_library(filter_status="review-ready")["sessions"]] == [older["capture_id"]]
    assert [session["capture_id"] for session in service.session_library(filter_status="exported")["sessions"]] == [newer["capture_id"]]
    assert [session["capture_id"] for session in service.session_library(filter_status="needs-attention")["sessions"]] == [failed["capture_id"]]


def test_search_scopes_deduplicate_noisy_matches_and_prefer_reviewed_content(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Search Polish")
    with connection_context(config.database_path) as connection:
        insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=int(created["id"]),
                capture_id=str(created["capture_id"]),
                description="Confirm the search polish action.",
                owner_name="Unknown",
                status="open",
                evidence_snippet="Confirm the search polish action.",
            ),
        )
        decision_id = insert_decision(
            connection,
            DecisionRecord(
                id=None,
                meeting_id=int(created["id"]),
                capture_id=str(created["capture_id"]),
                description="Search should show generated duplicate wording.",
                evidence_snippet="Decision: generated duplicate wording.",
            ),
        )
        connection.execute(
            """
            UPDATE decisions
            SET review_status = 'edited',
                reviewed_description = 'Search should show reviewed wording first.',
                reviewed_at = '2026-04-22T00:00:00+00:00'
            WHERE id = ?
            """,
            (decision_id,),
        )
        connection.commit()

    all_results = service.search_workspace("search", scope="all")
    action_results = service.search_workspace("search", scope="actions")
    decision_results = service.search_workspace("search", scope="decisions")

    assert all_results["raw_matches"] > all_results["total_matches"]
    assert action_results["total_matches"] == 1
    assert action_results["sessions"][0]["matches"][0]["item_type"] == "action"
    assert decision_results["total_matches"] == 1
    assert "reviewed wording" in decision_results["sessions"][0]["matches"][0]["snippet"]
    assert "generated duplicate" not in decision_results["sessions"][0]["matches"][0]["snippet"]


def test_search_handles_legacy_summary_schema_without_review_columns(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                capture_id TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                summary_type TEXT NOT NULL DEFAULT 'mock',
                evidence_snippet TEXT,
                provider_name TEXT NOT NULL DEFAULT 'heuristic',
                model_name TEXT,
                generated_at TEXT
            )
            """
        )
        connection.commit()

    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Legacy Summary Search")
    with connection_context(config.database_path) as connection:
        insert_summary(
            connection,
            SummaryRecord(
                id=None,
                meeting_id=int(created["id"]),
                capture_id=str(created["capture_id"]),
                title="Executive Summary",
                content="Legacy databases should still support local-first search.",
                summary_type="executive",
                evidence_snippet="Search should work after summary schema migration.",
            ),
        )
        connection.commit()

    result = service.search_workspace("local-first")

    assert result["total_matches"] >= 1
    assert any(group["capture_id"] == created["capture_id"] for group in result["sessions"])


def test_action_workflow_updates_persist_all_supported_states(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    created = service.create_session("Workflow States")
    with connection_context(config.database_path) as connection:
        action_id = insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=int(created["id"]),
                capture_id=str(created["capture_id"]),
                description="Track the follow-up workflow state.",
                owner_name="Unconfirmed speaker",
                status="open",
                evidence_snippet="Action: track workflow state.",
            ),
        )
        follow_up_id = insert_follow_up(
            connection,
            FollowUpRecord(
                id=None,
                meeting_id=int(created["id"]),
                capture_id=str(created["capture_id"]),
                description="Confirm whether workflow state refreshes correctly.",
                follow_up_type="follow_up",
                owner_name="Unknown",
                status="open",
                evidence_snippet="Follow up: confirm workflow state refresh.",
            ),
        )
        connection.commit()

    for workflow_status in ("open", "done", "dismissed", "carried_forward"):
        action = service.update_action_workflow_state(
            item_type="action",
            item_id=action_id,
            workflow_status=workflow_status,
        )
        follow_up = service.update_action_workflow_state(
            item_type="follow_up",
            item_id=follow_up_id,
            workflow_status=workflow_status,
        )

        assert action["workflow_state"] == workflow_status
        assert follow_up["workflow_state"] == workflow_status

        refreshed = service.dashboard_payload()["action_items"]
        states_by_key = {(item["item_type"], item["id"]): item["workflow_state"] for item in refreshed}
        assert states_by_key[("action", action_id)] == workflow_status
        assert states_by_key[("follow_up", follow_up_id)] == workflow_status

    reopened_service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    reopened_items = reopened_service.dashboard_payload()["action_items"]
    reopened_states = {(item["item_type"], item["id"]): item["workflow_state"] for item in reopened_items}
    assert reopened_states[("action", action_id)] == "carried_forward"
    assert reopened_states[("follow_up", follow_up_id)] == "carried_forward"


def test_action_workspace_filters_sorts_and_exposes_last_updated(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    bootstrap_database(config)
    service = SessionWorkflowService(
        config,
        audio_capture=FakeAudioCaptureService(),  # type: ignore[arg-type]
        transcription_engine=FakeNoopService(),  # type: ignore[arg-type]
        diarization_engine=FakeNoopService(),  # type: ignore[arg-type]
        summarizer=FakeNoopService(),  # type: ignore[arg-type]
        action_extractor=FakeNoopService(),  # type: ignore[arg-type]
        export_service=FakeExportService(),  # type: ignore[arg-type]
    )
    first = service.create_session("Alpha Session")
    second = service.create_session("Beta Session")
    with connection_context(config.database_path) as connection:
        open_action_id = insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=int(first["id"]),
                capture_id=str(first["capture_id"]),
                description="Open action for owner sorting.",
                owner_name="Zara",
                status="open",
                generated_at="2026-04-20T00:00:00+00:00",
            ),
        )
        done_action_id = insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=int(second["id"]),
                capture_id=str(second["capture_id"]),
                description="Done action should filter separately.",
                owner_name="Alex",
                status="done",
                generated_at="2026-04-21T00:00:00+00:00",
            ),
        )
        carried_follow_up_id = insert_follow_up(
            connection,
            FollowUpRecord(
                id=None,
                meeting_id=int(second["id"]),
                capture_id=str(second["capture_id"]),
                description="Carried follow-up remains active.",
                follow_up_type="follow_up",
                owner_name="Morgan",
                status="carried_forward",
                generated_at="2026-04-22T00:00:00+00:00",
            ),
        )
        insert_decision(
            connection,
            DecisionRecord(
                id=None,
                meeting_id=int(first["id"]),
                capture_id=str(first["capture_id"]),
                description="Decision should not appear in the action workspace.",
                generated_at="2026-04-23T00:00:00+00:00",
            ),
        )
        connection.execute(
            "UPDATE actions SET reviewed_at = '2026-04-24T00:00:00+00:00' WHERE id = ?",
            (done_action_id,),
        )
        connection.commit()

    active = service.action_workspace(workflow_filter="active", sort="recent")
    done = service.action_workspace(workflow_filter="done")
    owner_sorted = service.action_workspace(workflow_filter="all", sort="owner")
    session_sorted = service.action_workspace(workflow_filter="all", sort="session")

    assert {(item["item_type"], item["id"]) for item in active["items"]} == {
        ("action", open_action_id),
        ("follow_up", carried_follow_up_id),
    }
    assert [(item["item_type"], item["id"]) for item in done["items"]] == [("action", done_action_id)]
    assert [item["effective_owner_name"] for item in owner_sorted["items"]] == ["Alex", "Morgan", "Zara"]
    assert [item["source_display_name"] for item in session_sorted["items"]] == [
        "Alpha Session",
        "Beta Session",
        "Beta Session",
    ]
    assert done["items"][0]["last_updated_at"] == "2026-04-24T00:00:00+00:00"
