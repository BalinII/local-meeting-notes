from local_meeting_notes.export_service.service import _exportable_items, render_markdown
from local_meeting_notes.session_workflow.service import _related_capture_ids


def test_exportable_items_prefers_reviewed_for_final_notes():
    items = [
        {"id": 1, "review_status": "generated"},
        {"id": 2, "review_status": "accepted"},
        {"id": 3, "review_status": "edited"},
        {"id": 4, "review_status": "rejected"},
    ]
    result = _exportable_items(items, export_mode="final_notes")
    assert [item["id"] for item in result] == [2, 3]


def test_exportable_items_full_detail_excludes_rejected_only():
    items = [{"id": 1, "review_status": "generated"}, {"id": 2, "review_status": "rejected"}]
    result = _exportable_items(items, export_mode="full_detail")
    assert [item["id"] for item in result] == [1]


def test_related_capture_ids_matches_title_or_external_id():
    current = {"capture_id": "a", "title": "Weekly Sync", "external_meeting_id": "ext-1"}
    meetings = [
        {"capture_id": "a", "title": "Weekly Sync", "external_meeting_id": "ext-1"},
        {"capture_id": "b", "title": "Weekly Sync", "external_meeting_id": ""},
        {"capture_id": "c", "title": "Other", "external_meeting_id": "ext-1"},
        {"capture_id": "d", "title": "Other", "external_meeting_id": "ext-2"},
    ]
    related = _related_capture_ids(current, meetings)
    assert related == {"a", "b", "c"}


def test_render_markdown_final_notes_is_lightweight():
    payload = {
        "capture_id": "cap-1",
        "exported_at": "2026-05-04T10:00:00+00:00",
        "metadata": {"export_mode": "final_notes", "providers": [], "content_preference": "reviewed_first"},
        "summaries": [], "actions": [], "decisions": [], "follow_ups": [], "blockers_risks": [], "open_questions": [],
    }
    output = render_markdown(payload)
    assert "Final Notes" in output
    assert "## Export Metadata" not in output
