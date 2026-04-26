from __future__ import annotations

from pathlib import Path

from local_meeting_notes.config import load_config
from local_meeting_notes.models import ActionRecord, FollowUpRecord
from local_meeting_notes.session_workflow.service import SessionWorkflowService
from local_meeting_notes.storage.database import bootstrap_database, connection_context
from local_meeting_notes.storage.repository import insert_action, insert_follow_up, update_meeting_fields


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
    assert {item["workflow_state"] for item in items} == {"open", "blocked"}
