from __future__ import annotations

import json
from pathlib import Path

from local_meeting_notes.config import load_config
from local_meeting_notes.export_service.service import ExportService
from local_meeting_notes.models import ActionRecord, DecisionRecord, FollowUpRecord, SummaryRecord
from local_meeting_notes.storage.database import bootstrap_database, connection_context
from local_meeting_notes.storage.repository import (
    ensure_meeting_for_capture,
    insert_action,
    insert_decision,
    insert_follow_up,
    insert_summary,
    update_meeting_fields,
)


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


def _seed_outputs(config, capture_id: str = "capture-export") -> None:
    bootstrap_database(config)
    with connection_context(config.database_path) as connection:
        meeting_id = ensure_meeting_for_capture(connection, capture_id)
        update_meeting_fields(connection, capture_id, title=capture_id.replace("-", " ").title())
        insert_summary(
            connection,
            SummaryRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                title="Executive Summary",
                summary_type="executive",
                content="The team agreed to keep review and export local-first.",
                evidence_snippet="Decision: keep review and export local-first.",
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:00:00+00:00",
            ),
        )
        insert_summary(
            connection,
            SummaryRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                title="Detailed Summary",
                summary_type="detailed",
                content="Detailed Summary\nReview flow should be easy to scan before sharing.",
                evidence_snippet="The review screen needs a clearer detailed summary.",
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:01:00+00:00",
            ),
        )
        insert_summary(
            connection,
            SummaryRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                title="Detailed Summary",
                summary_type="detailed",
                content="Exports should preserve the same consolidated review structure.",
                evidence_snippet="Export should match the review payload.",
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:02:00+00:00",
            ),
        )
        insert_action(
            connection,
            ActionRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                description="Export Markdown, HTML, and JSON outputs.",
                owner_name="Unconfirmed speaker",
                evidence_snippet="Action item: export Markdown, HTML, and JSON.",
                start_offset_seconds=2,
                end_offset_seconds=8,
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:00:00+00:00",
            ),
        )
        insert_decision(
            connection,
            DecisionRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                description="Keep the review workflow local-first.",
                evidence_snippet="Decision: keep the review workflow local-first.",
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:00:00+00:00",
            ),
        )
        insert_follow_up(
            connection,
            FollowUpRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                description="Review extraction quality before sharing notes.",
                follow_up_type="blocker_risk",
                owner_name="Unknown",
                evidence_snippet="Risk: extraction quality still needs review.",
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:00:00+00:00",
            ),
        )
        insert_follow_up(
            connection,
            FollowUpRecord(
                id=None,
                meeting_id=meeting_id,
                capture_id=capture_id,
                description="Which export format should be shared by default?",
                follow_up_type="open_question",
                owner_name="Unconfirmed speaker",
                evidence_snippet="Open question: which export format is the default?",
                provider_name="local_llm",
                model_name="llama3.1:8b",
                generated_at="2026-04-23T00:00:00+00:00",
            ),
        )
        connection.commit()


def test_export_payload_groups_outputs_for_review(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_outputs(config)

    payload = ExportService(config).build_review_payload("capture-export")

    assert payload["capture_id"] == "capture-export"
    assert payload["metadata"]["providers"] == ["local_llm"]
    assert payload["metadata"]["summary_count"] == 2
    assert payload["metadata"]["persisted_summary_count"] == 3
    assert len(payload["summaries"]) == 2
    assert payload["summaries"][0]["title"] == "Executive Summary"
    assert payload["summaries"][1]["title"] == "Detailed Summary"
    assert "Review flow should be easy to scan" in payload["summaries"][1]["content"]
    assert "Exports should preserve the same consolidated review structure" in payload["summaries"][1]["content"]
    assert payload["summaries"][1]["content"].count("Detailed Summary") == 0
    assert "Export should match the review payload" in payload["summaries"][1]["evidence_snippet"]
    assert payload["actions"][0]["review_status"] == "generated"
    assert payload["actions"][0]["effective_description"] == payload["actions"][0]["description"]
    assert payload["actions"][0]["owner_name"] == "Unconfirmed speaker"
    assert payload["blockers_risks"][0]["description"] == "Review extraction quality before sharing notes."
    assert payload["open_questions"][0]["description"] == "Which export format should be shared by default?"


def test_export_service_renders_markdown_html_and_json(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_outputs(config)
    service = ExportService(config)

    markdown = service.render_export("capture-export", "markdown")
    html = service.render_export("capture-export", "html")
    payload = json.loads(service.render_export("capture-export", "json"))

    assert "# Capture Export" in markdown
    assert "## Executive Summary" in markdown
    assert "## Actions" in markdown
    assert "- Export mode: final_notes" in markdown
    assert markdown.count("## Detailed Summary") == 1
    assert "Evidence snippets" in markdown
    assert "<h1>Capture Export</h1>" in html
    assert html.count("<h2>Detailed Summary</h2>") == 1
    assert "Review status: generated" in html
    assert "<nav>" in html
    assert "Blockers / Risks" in html
    assert payload["metadata"]["action_count"] == 1
    assert payload["metadata"]["export_mode"] == "full_detail"


def test_reviewed_items_are_persisted_and_used_for_exports(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_outputs(config)
    service = ExportService(config)
    payload = service.build_review_payload("capture-export")
    action_id = payload["actions"][0]["id"]
    decision_id = payload["decisions"][0]["id"]

    edited = service.review_item(
        item_type="action",
        item_id=action_id,
        review_status="edited",
        reviewed_description="Share reviewed Markdown and HTML exports.",
        reviewed_owner_name="Ben",
    )
    service.review_item(
        item_type="decision",
        item_id=decision_id,
        review_status="rejected",
    )

    next_payload = service.build_review_payload("capture-export")
    markdown = service.render_export("capture-export", "markdown")
    html = service.render_export("capture-export", "html")

    assert edited["review_status"] == "edited"
    assert edited["effective_description"] == "Share reviewed Markdown and HTML exports."
    assert edited["effective_owner_name"] == "Ben"
    assert next_payload["actions"][0]["reviewed_description"] == "Share reviewed Markdown and HTML exports."
    assert "Share reviewed Markdown and HTML exports. [Ben]" in markdown
    assert "Export Markdown, HTML, and JSON outputs." not in markdown
    assert "Keep the review workflow local-first." not in markdown
    assert "Share reviewed Markdown and HTML exports." in html
    assert "Review status: edited" in html
    assert "Keep the review workflow local-first." not in html


def test_final_notes_prefers_reviewed_items_but_full_detail_keeps_generated(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_outputs(config)
    service = ExportService(config)
    payload = service.build_review_payload("capture-export")
    action_id = payload["actions"][0]["id"]
    service.review_item(
        item_type="action",
        item_id=action_id,
        review_status="accepted",
    )

    markdown = service.render_export("capture-export", "markdown")
    json_payload = json.loads(service.render_export("capture-export", "json"))
    assert "Review status: accepted" in markdown
    assert json_payload["metadata"]["export_mode"] == "full_detail"


def test_export_service_writes_files(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_outputs(config)
    service = ExportService(config)

    markdown_path = service.export_capture("capture-export", "markdown")
    html_path = service.export_capture("capture-export", "html")
    json_path = service.export_capture("capture-export", "json")

    assert markdown_path.name.endswith(".md")
    assert html_path.name.endswith(".html")
    assert json_path.name.endswith(".json")
    assert markdown_path.name.startswith("capture-export-")
    assert html_path.name.startswith("capture-export-")
    assert json_path.name.startswith("capture-export-")
    assert markdown_path.exists()
    assert html_path.exists()
    assert json_path.exists()


def test_recent_captures_include_review_metadata(local_tmp_dir) -> None:
    config = _build_config(local_tmp_dir)
    _seed_outputs(config, capture_id="capture-older")
    _seed_outputs(config, capture_id="capture-newer")
    service = ExportService(config)

    newer_payload = service.build_review_payload("capture-newer")
    action_id = newer_payload["actions"][0]["id"]
    service.review_item(
        item_type="action",
        item_id=action_id,
        review_status="accepted",
    )

    recent = service.list_recent_captures(limit=5)

    captures_by_id = {item["capture_id"]: item for item in recent}
    assert set(captures_by_id) == {"capture-newer", "capture-older"}
    assert captures_by_id["capture-newer"]["display_name"] == "Capture Newer"
    assert captures_by_id["capture-newer"]["has_reviewed_items"] is True
    assert captures_by_id["capture-newer"]["latest_generated_at"] == "2026-04-23T00:02:00+00:00"
    assert captures_by_id["capture-newer"]["latest_reviewed_at"] is not None
    assert captures_by_id["capture-newer"]["providers"] == ["local_llm"]
    assert captures_by_id["capture-newer"]["models"] == ["llama3.1:8b"]
    assert captures_by_id["capture-older"]["has_reviewed_items"] is False
