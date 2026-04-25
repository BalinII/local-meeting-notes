from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout

from local_meeting_notes.app import main
from local_meeting_notes.config import load_config
from local_meeting_notes.export_service.service import ExportService
from local_meeting_notes.models import ActionRecord, SummaryRecord
from local_meeting_notes.storage.database import bootstrap_database, connection_context
from local_meeting_notes.storage.repository import ensure_meeting_for_capture, insert_action, insert_summary


def test_review_recent_lists_capture_metadata(local_tmp_dir) -> None:
    env_root = local_tmp_dir / "data"
    os.environ["LMN_DATA_DIR"] = str(env_root)
    os.environ["AUDIO_OUTPUT_DIR"] = str(env_root / "audio")
    os.environ["DATABASE_PATH"] = str(env_root / "local_meeting_notes.db")
    os.environ["TRANSCRIPT_OUTPUT_DIR"] = str(env_root / "transcripts")
    os.environ["EXPORT_OUTPUT_DIR"] = str(env_root / "exports")
    os.environ["TEMP_OUTPUT_DIR"] = str(env_root / "tmp")
    os.environ["LOG_DIR"] = str(env_root / "logs")
    os.environ["SESSION_STATE_PATH"] = str(env_root / "tmp" / "session.json")
    os.environ["AUDIO_CAPTURE_STATE_PATH"] = str(env_root / "tmp" / "audio_capture_state.json")

    try:
        config = load_config()
        bootstrap_database(config)
        with connection_context(config.database_path) as connection:
            meeting_id = ensure_meeting_for_capture(connection, "capture-review-cli")
            insert_summary(
                connection,
                SummaryRecord(
                    id=None,
                    meeting_id=meeting_id,
                    capture_id="capture-review-cli",
                    title="Executive Summary",
                    summary_type="executive",
                    content="A concise summary.",
                    evidence_snippet="Decision: keep things local.",
                    provider_name="local_llm",
                    model_name="llama3.1:8b",
                    generated_at="2026-04-23T00:00:00+00:00",
                ),
            )
            insert_action(
                connection,
                ActionRecord(
                    id=None,
                    meeting_id=meeting_id,
                    capture_id="capture-review-cli",
                    description="Review the capture.",
                    owner_name="Unconfirmed speaker",
                    evidence_snippet="Action item: review the capture.",
                    provider_name="local_llm",
                    model_name="llama3.1:8b",
                    generated_at="2026-04-23T00:00:00+00:00",
                ),
            )
            connection.commit()

        service = ExportService(config)
        payload = service.build_review_payload("capture-review-cli")
        action_id = payload["actions"][0]["id"]
        service.review_item(item_type="action", item_id=action_id, review_status="accepted")

        out = io.StringIO()
        with redirect_stdout(out):
            assert main(["review", "recent", "--limit", "5"]) == 0
        parsed = json.loads(out.getvalue())
        assert parsed[0]["capture_id"] == "capture-review-cli"
        assert parsed[0]["has_reviewed_items"] is True
    finally:
        for key in (
            "LMN_DATA_DIR",
            "AUDIO_OUTPUT_DIR",
            "DATABASE_PATH",
            "TRANSCRIPT_OUTPUT_DIR",
            "EXPORT_OUTPUT_DIR",
            "TEMP_OUTPUT_DIR",
            "LOG_DIR",
            "SESSION_STATE_PATH",
            "AUDIO_CAPTURE_STATE_PATH",
        ):
            os.environ.pop(key, None)
