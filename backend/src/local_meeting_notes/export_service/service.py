"""Export and review payload service for persisted meeting-note outputs."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    fetch_meeting_by_capture_id,
    fetch_actions_for_capture,
    fetch_decisions_for_capture,
    fetch_follow_ups_for_capture,
    fetch_recent_capture_activity,
    fetch_summaries_for_capture,
    update_meeting_fields,
    update_extracted_item_review,
)


EXPORT_FORMATS = {"markdown", "html", "json"}
REVIEW_STATUSES = {"generated", "accepted", "edited", "rejected"}
EXPORT_MODES = {"final_notes", "full_detail"}


class ExportService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_review_payload(self, capture_id: str, export_mode: str = "full_detail") -> dict[str, Any]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            meeting = fetch_meeting_by_capture_id(connection, capture_id)
            raw_summaries = [
                dict(row) for row in fetch_summaries_for_capture(connection, capture_id)
            ]
            actions = [dict(row) for row in fetch_actions_for_capture(connection, capture_id)]
            decisions = [dict(row) for row in fetch_decisions_for_capture(connection, capture_id)]
            follow_ups = [dict(row) for row in fetch_follow_ups_for_capture(connection, capture_id)]

        mode = _resolve_export_mode("json", export_mode)
        summaries = _consolidate_summaries(raw_summaries)
        actions = [_with_review_fields(item, "action") for item in actions]
        decisions = [_with_review_fields(item, "decision") for item in decisions]
        follow_ups = [_with_review_fields(item, "follow_up") for item in follow_ups]
        blockers_risks = [item for item in follow_ups if item["follow_up_type"] == "blocker_risk"]
        open_questions = [item for item in follow_ups if item["follow_up_type"] == "open_question"]
        other_follow_ups = [item for item in follow_ups if item["follow_up_type"] == "follow_up"]

        providers = sorted(
            {
                str(item["provider_name"])
                for collection in (raw_summaries, actions, decisions, follow_ups)
                for item in collection
                if item.get("provider_name")
            }
        )
        generated_values = [
            str(item["generated_at"])
            for collection in (raw_summaries, actions, decisions, follow_ups)
            for item in collection
            if item.get("generated_at")
        ]

        return {
            "capture_id": capture_id,
            "exported_at": _now_timestamp(),
            "metadata": {
                "display_name": str(meeting["title"]) if meeting is not None else None,
                "content_state": _content_state_for_meeting(meeting),
                "export_mode": mode,
                "content_preference": "reviewed_first",
                "providers": providers,
                "latest_generated_at": max(generated_values) if generated_values else None,
                "summary_count": len(summaries),
                "persisted_summary_count": len(raw_summaries),
                "action_count": len(actions),
                "decision_count": len(decisions),
                "follow_up_count": len(follow_ups),
            },
            "summaries": summaries,
            "actions": actions,
            "decisions": decisions,
            "follow_ups": other_follow_ups,
            "blockers_risks": blockers_risks,
            "open_questions": open_questions,
        }

    def list_recent_captures(self, limit: int = 12) -> list[dict[str, Any]]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            rows = fetch_recent_capture_activity(connection, limit=limit)

        captures: list[dict[str, Any]] = []
        for row in rows:
            captures.append(
                {
                    "capture_id": row["capture_id"],
                    "display_name": row["display_name"],
                    "created_at": row["first_generated_at"],
                    "latest_generated_at": row["latest_generated_at"],
                    "latest_reviewed_at": row["latest_reviewed_at"],
                    "providers": _split_csv_values(row["providers"]),
                    "models": _split_csv_values(row["models"]),
                    "has_reviewed_items": bool(row["has_reviewed_items"]),
                }
            )
        return captures

    def review_item(
        self,
        *,
        item_type: str,
        item_id: int,
        review_status: str,
        reviewed_description: str | None = None,
        reviewed_owner_name: str | None = None,
    ) -> dict[str, Any]:
        if review_status not in REVIEW_STATUSES:
            raise ValueError(f"Unsupported review status: {review_status}")
        if item_type not in {"action", "decision", "follow_up"}:
            raise ValueError(f"Unsupported review item type: {item_type}")

        reviewed_at = _now_timestamp()
        description = _clean_review_text(reviewed_description)
        owner_name = _clean_review_text(reviewed_owner_name)
        if review_status in {"generated", "accepted", "rejected"}:
            description = None
            owner_name = None

        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            row = update_extracted_item_review(
                connection,
                item_type=item_type,
                item_id=item_id,
                review_status=review_status,
                reviewed_description=description,
                reviewed_owner_name=owner_name,
                reviewed_at=reviewed_at,
            )
            if row is not None:
                meeting = fetch_meeting_by_capture_id(connection, str(row["capture_id"]))
                if meeting is not None:
                    next_status = "reviewed" if str(meeting["status"]) == "review_ready" else str(meeting["status"])
                    update_meeting_fields(
                        connection,
                        str(row["capture_id"]),
                        has_reviewed_items=1 if review_status != "generated" else meeting["has_reviewed_items"],
                        reviewed_at=reviewed_at if review_status != "generated" else meeting["reviewed_at"],
                        status=next_status,
                        updated_at=reviewed_at,
                    )
            connection.commit()

        if row is None:
            raise ValueError(f"No {item_type} found with id {item_id}.")
        return _with_review_fields(dict(row), item_type)

    def render_export(self, capture_id: str, export_format: str, export_mode: str | None = None) -> str:
        payload = self.build_review_payload(capture_id, export_mode=_resolve_export_mode(export_format, export_mode))
        return _render_payload(payload=payload, export_format=export_format)

    def export_capture(self, capture_id: str, export_format: str, export_mode: str | None = None) -> Path:
        if export_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported export format: {export_format}")
        payload = self.build_review_payload(capture_id, export_mode=_resolve_export_mode(export_format, export_mode))
        content = _render_payload(payload=payload, export_format=export_format)
        extension = "md" if export_format == "markdown" else export_format
        output_dir = self.config.export_output_dir / capture_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / _build_export_filename(payload=payload, extension=extension)
        output_path.write_text(content, encoding="utf-8")
        return output_path


def _render_payload(*, payload: dict[str, Any], export_format: str) -> str:
    if export_format == "json":
        return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if export_format == "markdown":
        return render_markdown(payload)
    if export_format == "html":
        return render_html(payload)
    raise ValueError(f"Unsupported export format: {export_format}")


def _content_state_for_meeting(meeting: Any) -> str:
    if meeting is None:
        return "generated"
    state = str(meeting["status"] or "generated")
    if state == "final":
        return "final"
    if state in {"reviewed", "exported"} or bool(meeting["has_reviewed_items"]):
        return "reviewed"
    return "generated"


def render_markdown(payload: dict[str, Any]) -> str:
    export_mode = str(payload.get("metadata", {}).get("export_mode") or "final_notes")
    display_name = _display_name(payload)
    lines = [
        f"# {display_name}",
        "",
        "## Export Metadata",
        "",
        f"- Capture ID: `{payload['capture_id']}`",
        f"- Export mode: {export_mode}",
        f"- Content preference: {payload['metadata'].get('content_preference', 'reviewed_first')}",
        f"- Exported: {payload['exported_at']}",
        f"- Providers: {', '.join(payload['metadata']['providers']) or 'Unknown'}",
    ]
    model_names = _provider_model_names(payload)
    if model_names:
        lines.append(f"- Models: {', '.join(model_names)}")
    if payload["metadata"].get("latest_generated_at"):
        lines.append(f"- Latest generated: {payload['metadata']['latest_generated_at']}")
    lines.append("")

    lines.extend(_markdown_summaries(payload))
    lines.extend(_markdown_items("Actions", payload["actions"], include_owner=True, export_mode=export_mode))
    lines.extend(_markdown_items("Decisions", payload["decisions"], export_mode=export_mode))
    lines.extend(_markdown_items("Follow-ups", payload["follow_ups"], include_owner=True, export_mode=export_mode))
    lines.extend(_markdown_items("Blockers / Risks", payload["blockers_risks"], include_owner=True, export_mode=export_mode))
    lines.extend(_markdown_items("Open Questions", payload["open_questions"], include_owner=True, export_mode=export_mode))
    return "\n".join(lines).rstrip() + "\n"


def render_html(payload: dict[str, Any]) -> str:
    export_mode = str(payload.get("metadata", {}).get("export_mode") or "final_notes")
    display_name = _display_name(payload)
    body = [
        f"<h1>{html.escape(display_name)}</h1>",
        f"<p class=\"capture-id\"><strong>Capture ID:</strong> <code>{html.escape(payload['capture_id'])}</code></p>",
        "<nav><a href=\"#executive-summary\">Executive Summary</a><a href=\"#detailed-summary\">Detailed Summary</a><a href=\"#actions\">Actions</a><a href=\"#decisions\">Decisions</a><a href=\"#follow-ups\">Follow-ups</a><a href=\"#blockers-risks\">Blockers / Risks</a><a href=\"#open-questions\">Open Questions</a></nav>",
        "<section class=\"metadata\" id=\"metadata\">",
        f"<p><strong>Exported:</strong> {html.escape(payload['exported_at'])}</p>",
        f"<p><strong>Content preference:</strong> {html.escape(str(payload['metadata'].get('content_preference', 'reviewed_first')))}</p>",
        f"<p><strong>Providers:</strong> {html.escape(', '.join(payload['metadata']['providers']) or 'Unknown')}</p>",
        f"<p><strong>Models:</strong> {html.escape(', '.join(_provider_model_names(payload)) or 'Unknown')}</p>",
        "</section>",
        _html_summaries(payload),
        _html_items("Actions", payload["actions"], include_owner=True, export_mode=export_mode),
        _html_items("Decisions", payload["decisions"], export_mode=export_mode),
        _html_items("Follow-ups", payload["follow_ups"], include_owner=True, export_mode=export_mode),
        _html_items("Blockers / Risks", payload["blockers_risks"], include_owner=True, export_mode=export_mode),
        _html_items("Open Questions", payload["open_questions"], include_owner=True, export_mode=export_mode),
    ]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(display_name)}</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 36px auto; max-width: 980px; color: #182033; line-height: 1.55; padding: 0 18px; }}
    nav {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 14px 0 20px; }}
    nav a {{ color: #2455a6; text-decoration: none; font-size: 0.95rem; }}
    nav a:hover {{ text-decoration: underline; }}
    section {{ margin: 24px 0; border-top: 1px solid #e2e8f0; padding-top: 18px; }}
    article, li {{ margin-bottom: 14px; }}
    .capture-id {{ color: #516178; margin-top: -6px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #edf2f7; font-size: 12px; }}
    .reviewed {{ background: #def7ec; color: #03543f; }}
    .edited {{ background: #e5edff; color: #1e429f; }}
    .uncertain {{ background: #fff8e1; border-left: 3px solid #f7c948; padding: 8px 10px; color: #744210; font-size: 0.92em; }}
    .evidence {{ color: #5b6678; font-size: 0.92em; white-space: pre-line; margin-top: 8px; }}
    .summary-content {{ white-space: pre-line; }}
    @media print {{
      body {{ margin: 16px; max-width: none; color: #000; }}
      nav {{ display: none; }}
      section {{ break-inside: avoid; page-break-inside: avoid; }}
      a {{ color: #000; }}
    }}
  </style>
</head>
<body>
{''.join(body)}
</body>
</html>
"""


def _markdown_summaries(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    summaries = payload["summaries"]
    if not summaries:
        return ["## Executive Summary", "", "No summary found.", "", "## Detailed Summary", "", "No summary found.", ""]
    for summary in summaries:
        section_title = str(summary["title"])
        lines.extend(
            [
                f"## {section_title}",
                "",
                str(summary["content"]),
                "",
                f"_ {_metadata_line(summary)}",
            ]
        )
        if summary.get("evidence_snippet"):
            lines.append("")
            lines.append("<details><summary>Evidence snippets</summary>")
            lines.append("")
            evidence_lines = _split_evidence_lines(str(summary["evidence_snippet"]))
            lines.extend(f"- {line}" for line in evidence_lines)
            lines.append("")
            lines.append("</details>")
            lines.append("")
    return lines


def _consolidate_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    executive = _summaries_of_type(summaries, "executive")
    detailed = _summaries_of_type(summaries, "detailed")
    consolidated = []
    if executive:
        consolidated.append(_consolidate_summary_group(executive, "Executive Summary", "executive"))
    if detailed:
        consolidated.append(_consolidate_summary_group(detailed, "Detailed Summary", "detailed"))
    return consolidated


def _summaries_of_type(summaries: list[dict[str, Any]], summary_type: str) -> list[dict[str, Any]]:
    return [
        summary
        for summary in summaries
        if str(summary.get("summary_type", "")).lower() == summary_type
    ]


def _consolidate_summary_group(
    summaries: list[dict[str, Any]], title: str, summary_type: str
) -> dict[str, Any]:
    if len(summaries) == 1:
        summary = dict(summaries[0])
        summary["title"] = title
        summary["summary_type"] = summary_type
        return summary

    first = summaries[0]
    return {
        "id": first.get("id"),
        "meeting_id": first.get("meeting_id"),
        "capture_id": first.get("capture_id"),
        "title": title,
        "summary_type": summary_type,
        "content": _join_summary_content(summaries, title),
        "evidence_snippet": _join_summary_evidence(summaries),
        "provider_name": _combined_value(summaries, "provider_name"),
        "model_name": _combined_value(summaries, "model_name"),
        "generated_at": _latest_value(summaries, "generated_at"),
    }


def _join_summary_content(summaries: list[dict[str, Any]], title: str) -> str:
    sections = [
        _strip_duplicate_heading(str(summary.get("content") or ""), title)
        for summary in summaries
    ]
    return "\n\n".join(section for section in sections if section).strip()


def _join_summary_evidence(summaries: list[dict[str, Any]]) -> str | None:
    snippets = [
        str(summary["evidence_snippet"]).strip()
        for summary in summaries
        if summary.get("evidence_snippet")
    ]
    if not snippets:
        return None
    return "\n".join(f"- {snippet}" for snippet in snippets)


def _strip_duplicate_heading(content: str, title: str) -> str:
    lines = content.strip().splitlines()
    while lines and _normalized_heading(lines[0]) == _normalized_heading(title):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _normalized_heading(value: str) -> str:
    return value.strip().strip("#:").strip().casefold()


def _combined_value(summaries: list[dict[str, Any]], key: str) -> str | None:
    values = sorted({str(summary[key]) for summary in summaries if summary.get(key)})
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return "Multiple"


def _latest_value(summaries: list[dict[str, Any]], key: str) -> str | None:
    values = [str(summary[key]) for summary in summaries if summary.get(key)]
    return max(values) if values else None


def _split_csv_values(value: Any) -> list[str]:
    if not value or not isinstance(value, str):
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _display_name(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata", {})
    display_name = _clean_review_text(metadata.get("display_name")) if isinstance(metadata, dict) else None
    if display_name:
        return display_name
    capture_id = str(payload["capture_id"])
    words = [segment for segment in re.split(r"[-_]+", capture_id) if segment]
    pretty_capture_id = " ".join(word.capitalize() for word in words) if words else capture_id
    return f"Meeting Notes - {pretty_capture_id}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    return slug or "meeting-notes"


def _provider_model_names(payload: dict[str, Any]) -> list[str]:
    names = sorted(
        {
            str(item["model_name"])
            for collection_name in (
                "summaries",
                "actions",
                "decisions",
                "follow_ups",
                "blockers_risks",
                "open_questions",
            )
            for item in payload.get(collection_name, [])
            if item.get("model_name")
        }
    )
    return names


def _split_evidence_lines(value: str) -> list[str]:
    lines = [line.strip().lstrip("-").strip() for line in value.splitlines() if line.strip()]
    return lines or [value.strip()]


def _review_status_label(item: dict[str, Any]) -> str:
    status = str(item.get("review_status") or "generated")
    return f"Review status: {status}"


def _uncertainty_note(item: dict[str, Any]) -> str | None:
    evidence = str(item.get("evidence_snippet") or "").lower()
    owner = _owner_label(item)
    notes: list[str] = []
    if "unknown" in owner.casefold() or "unconfirmed" in owner.casefold():
        notes.append("Owner is not confirmed.")
    if "weak evidence" in evidence:
        notes.append("Evidence may be weak.")
    return " ".join(notes) if notes else None


def _build_export_filename(*, payload: dict[str, Any], extension: str) -> str:
    exported_date = str(payload.get("exported_at") or "").split("T")[0]
    if not exported_date:
        exported_date = datetime.now(timezone.utc).date().isoformat()
    display_part = _slugify(_display_name(payload))
    mode = str(payload.get("metadata", {}).get("export_mode") or "final_notes").replace("_", "-")
    return f"{display_part}-{mode}-{exported_date}.{extension}"


def _markdown_items(
    title: str, items: list[dict[str, Any]], *, include_owner: bool = False, export_mode: str = "final_notes"
) -> list[str]:
    lines = [f"## {title}", ""]
    exportable_items = _exportable_items(items, export_mode=export_mode)
    if not exportable_items:
        return lines + [f"No {title.lower()} found.", ""]
    for item in exportable_items:
        owner = f" [{_owner_label(item)}]" if include_owner else ""
        lines.append(f"- {_effective_description(item)}{owner}")
        lines.append(f"  - Status: {_review_status_label(item)}")
        if item.get("start_offset_seconds") is not None:
            lines.append(f"  - Time: {item['start_offset_seconds']}-{item['end_offset_seconds']}s")
        lines.append(f"  - {_metadata_line(item)}")
        uncertainty = _uncertainty_note(item)
        if uncertainty:
            lines.append(f"  - Uncertainty: {uncertainty}")
        if item.get("evidence_snippet"):
            lines.append("  - Evidence:")
            for evidence_line in _split_evidence_lines(str(item["evidence_snippet"])):
                lines.append(f"    - {evidence_line}")
    lines.append("")
    return lines


def _html_summaries(payload: dict[str, Any]) -> str:
    summaries = payload["summaries"]
    if not summaries:
        return "<section id=\"executive-summary\"><h2>Executive Summary</h2><p>No summary found.</p></section><section id=\"detailed-summary\"><h2>Detailed Summary</h2><p>No summary found.</p></section>"
    articles = []
    for summary in summaries:
        summary_title = str(summary["title"])
        section_id = _slugify(summary_title)
        evidence = _html_evidence(summary)
        articles.append(
            f"<section id=\"{html.escape(section_id)}\"><h2>{html.escape(summary_title)}</h2>"
            f"<article><p class=\"summary-content\">{html.escape(str(summary['content']))}</p>"
            f"<p class=\"badge\">{html.escape(_metadata_line(summary))}</p>{evidence}</article></section>"
        )
    return "".join(articles)


def _html_items(
    title: str, items: list[dict[str, Any]], *, include_owner: bool = False, export_mode: str = "final_notes"
) -> str:
    section_id = _slugify(title)
    exportable_items = _exportable_items(items, export_mode=export_mode)
    if not exportable_items:
        return f"<section id=\"{html.escape(section_id)}\"><h2>{html.escape(title)}</h2><p>No {html.escape(title.lower())} found.</p></section>"
    rows = []
    for item in exportable_items:
        owner = f" <span class=\"badge\">{html.escape(_owner_label(item))}</span>" if include_owner else ""
        status_class = "badge"
        if item.get("review_status") == "accepted":
            status_class = "badge reviewed"
        elif item.get("review_status") == "edited":
            status_class = "badge edited"
        timing = ""
        if item.get("start_offset_seconds") is not None:
            timing = f"<p class=\"evidence\">Time: {item['start_offset_seconds']}-{item['end_offset_seconds']}s</p>"
        uncertainty = _uncertainty_note(item)
        uncertainty_block = (
            f"<p class=\"uncertain\"><strong>Uncertainty:</strong> {html.escape(uncertainty)}</p>"
            if uncertainty
            else ""
        )
        rows.append(
            f"<li><strong>{html.escape(_effective_description(item))}</strong>{owner}"
            f"<p class=\"{status_class}\">{html.escape(_review_status_label(item))}</p>"
            f"{timing}<p class=\"badge\">{html.escape(_metadata_line(item))}</p>{uncertainty_block}{_html_evidence(item)}</li>"
        )
    return f"<section id=\"{html.escape(section_id)}\"><h2>{html.escape(title)}</h2><ul>{''.join(rows)}</ul></section>"


def _html_evidence(item: dict[str, Any]) -> str:
    if not item.get("evidence_snippet"):
        return ""
    evidence_rows = "".join(
        f"<li>{html.escape(line)}</li>" for line in _split_evidence_lines(str(item["evidence_snippet"]))
    )
    return f"<details><summary>Evidence snippets</summary><ul class=\"evidence\">{evidence_rows}</ul></details>"


def _metadata_line(item: dict[str, Any]) -> str:
    model = f" / {item['model_name']}" if item.get("model_name") else ""
    generated = f" / {item['generated_at']}" if item.get("generated_at") else ""
    return f"Provider: {item.get('provider_name') or 'Unknown'}{model}{generated}"


def _owner_label(item: dict[str, Any]) -> str:
    owner = item.get("effective_owner_name") or item.get("owner_name") or "Unconfirmed speaker"
    if owner in {"Unknown", "Unconfirmed speaker"}:
        return f"{owner} - review ownership"
    return str(owner)


def _with_review_fields(item: dict[str, Any], item_type: str) -> dict[str, Any]:
    review_status = item.get("review_status") or "generated"
    reviewed_description = _clean_review_text(item.get("reviewed_description"))
    reviewed_owner_name = _clean_review_text(item.get("reviewed_owner_name"))
    item["item_type"] = item_type
    item["review_status"] = review_status
    item["effective_description"] = reviewed_description or str(item.get("description") or "")
    item["effective_owner_name"] = reviewed_owner_name or item.get("owner_name")
    item["is_rejected"] = review_status == "rejected"
    return item


def _exportable_items(items: list[dict[str, Any]], *, export_mode: str = "final_notes") -> list[dict[str, Any]]:
    filtered = [item for item in items if item.get("review_status") != "rejected"]
    if export_mode == "full_detail":
        return filtered
    preferred = [item for item in filtered if item.get("review_status") in {"accepted", "edited"}]
    return preferred or filtered


def _resolve_export_mode(export_format: str, export_mode: str | None = None) -> str:
    if export_mode in EXPORT_MODES:
        return export_mode
    if export_format == "json":
        return "full_detail"
    return "final_notes"


def _effective_description(item: dict[str, Any]) -> str:
    return str(item.get("effective_description") or item.get("description") or "")


def _clean_review_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _now_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
