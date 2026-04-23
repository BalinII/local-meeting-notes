"""Export and review payload service for persisted meeting-note outputs."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..storage.database import bootstrap_database, connection_context
from ..storage.repository import (
    fetch_actions_for_capture,
    fetch_decisions_for_capture,
    fetch_follow_ups_for_capture,
    fetch_summaries_for_capture,
    update_extracted_item_review,
)


EXPORT_FORMATS = {"markdown", "html", "json"}
REVIEW_STATUSES = {"generated", "accepted", "edited", "rejected"}


class ExportService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_review_payload(self, capture_id: str) -> dict[str, Any]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            raw_summaries = [
                dict(row) for row in fetch_summaries_for_capture(connection, capture_id)
            ]
            actions = [dict(row) for row in fetch_actions_for_capture(connection, capture_id)]
            decisions = [dict(row) for row in fetch_decisions_for_capture(connection, capture_id)]
            follow_ups = [dict(row) for row in fetch_follow_ups_for_capture(connection, capture_id)]

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
            connection.commit()

        if row is None:
            raise ValueError(f"No {item_type} found with id {item_id}.")
        return _with_review_fields(dict(row), item_type)

    def render_export(self, capture_id: str, export_format: str) -> str:
        payload = self.build_review_payload(capture_id)
        if export_format == "json":
            return json.dumps(payload, indent=2, ensure_ascii=False)
        if export_format == "markdown":
            return render_markdown(payload)
        if export_format == "html":
            return render_html(payload)
        raise ValueError(f"Unsupported export format: {export_format}")

    def export_capture(self, capture_id: str, export_format: str) -> Path:
        if export_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported export format: {export_format}")
        content = self.render_export(capture_id, export_format)
        extension = "md" if export_format == "markdown" else export_format
        output_dir = self.config.export_output_dir / capture_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"meeting-notes.{extension}"
        output_path.write_text(content, encoding="utf-8")
        return output_path


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Meeting Notes: {payload['capture_id']}",
        "",
        f"- Exported: {payload['exported_at']}",
        f"- Providers: {', '.join(payload['metadata']['providers']) or 'Unknown'}",
    ]
    if payload["metadata"].get("latest_generated_at"):
        lines.append(f"- Latest generated: {payload['metadata']['latest_generated_at']}")
    lines.append("")

    lines.extend(_markdown_summaries(payload["summaries"]))
    lines.extend(_markdown_items("Actions", payload["actions"], include_owner=True))
    lines.extend(_markdown_items("Decisions", payload["decisions"]))
    lines.extend(_markdown_items("Follow-ups", payload["follow_ups"], include_owner=True))
    lines.extend(_markdown_items("Blockers / Risks", payload["blockers_risks"], include_owner=True))
    lines.extend(_markdown_items("Open Questions", payload["open_questions"], include_owner=True))
    return "\n".join(lines).rstrip() + "\n"


def render_html(payload: dict[str, Any]) -> str:
    body = [
        f"<h1>Meeting Notes: {html.escape(payload['capture_id'])}</h1>",
        "<section class=\"metadata\">",
        f"<p><strong>Exported:</strong> {html.escape(payload['exported_at'])}</p>",
        f"<p><strong>Providers:</strong> {html.escape(', '.join(payload['metadata']['providers']) or 'Unknown')}</p>",
        "</section>",
        _html_summaries(payload["summaries"]),
        _html_items("Actions", payload["actions"], include_owner=True),
        _html_items("Decisions", payload["decisions"]),
        _html_items("Follow-ups", payload["follow_ups"], include_owner=True),
        _html_items("Blockers / Risks", payload["blockers_risks"], include_owner=True),
        _html_items("Open Questions", payload["open_questions"], include_owner=True),
    ]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Meeting Notes: {html.escape(payload['capture_id'])}</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 40px; color: #182033; line-height: 1.55; }}
    section {{ margin: 28px 0; }}
    article, li {{ margin-bottom: 14px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #edf2f7; font-size: 12px; }}
    .evidence {{ color: #5b6678; font-size: 0.92em; white-space: pre-line; }}
  </style>
</head>
<body>
{''.join(body)}
</body>
</html>
"""


def _markdown_summaries(summaries: list[dict[str, Any]]) -> list[str]:
    lines = ["## Summaries", ""]
    if not summaries:
        return lines + ["No summaries found.", ""]
    for summary in summaries:
        lines.extend(
            [
                f"### {summary['title']}",
                "",
                str(summary["content"]),
                "",
                _metadata_line(summary),
            ]
        )
        if summary.get("evidence_snippet"):
            evidence_lines = str(summary["evidence_snippet"]).splitlines()
            lines.append("> Evidence:")
            lines.extend(f"> {line}" for line in evidence_lines)
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


def _markdown_items(
    title: str, items: list[dict[str, Any]], *, include_owner: bool = False
) -> list[str]:
    lines = [f"## {title}", ""]
    exportable_items = _exportable_items(items)
    if not exportable_items:
        return lines + [f"No {title.lower()} found.", ""]
    for item in exportable_items:
        owner = f" [{_owner_label(item)}]" if include_owner else ""
        lines.append(f"- {_effective_description(item)}{owner}")
        if item.get("start_offset_seconds") is not None:
            lines.append(f"  - Time: {item['start_offset_seconds']}-{item['end_offset_seconds']}s")
        lines.append(f"  - {_metadata_line(item)}")
        if item.get("evidence_snippet"):
            lines.append(f"  - Evidence: {item['evidence_snippet']}")
    lines.append("")
    return lines


def _html_summaries(summaries: list[dict[str, Any]]) -> str:
    if not summaries:
        return "<section><h2>Summaries</h2><p>No summaries found.</p></section>"
    articles = []
    for summary in summaries:
        evidence = _html_evidence(summary)
        articles.append(
            f"<article><h3>{html.escape(str(summary['title']))}</h3>"
            f"<p>{html.escape(str(summary['content']))}</p>"
            f"<p class=\"badge\">{html.escape(_metadata_line(summary))}</p>{evidence}</article>"
        )
    return f"<section><h2>Summaries</h2>{''.join(articles)}</section>"


def _html_items(title: str, items: list[dict[str, Any]], *, include_owner: bool = False) -> str:
    exportable_items = _exportable_items(items)
    if not exportable_items:
        return f"<section><h2>{html.escape(title)}</h2><p>No {html.escape(title.lower())} found.</p></section>"
    rows = []
    for item in exportable_items:
        owner = f" <span class=\"badge\">{html.escape(_owner_label(item))}</span>" if include_owner else ""
        timing = ""
        if item.get("start_offset_seconds") is not None:
            timing = f"<p class=\"evidence\">Time: {item['start_offset_seconds']}-{item['end_offset_seconds']}s</p>"
        rows.append(
            f"<li><strong>{html.escape(_effective_description(item))}</strong>{owner}"
            f"{timing}<p class=\"badge\">{html.escape(_metadata_line(item))}</p>{_html_evidence(item)}</li>"
        )
    return f"<section><h2>{html.escape(title)}</h2><ul>{''.join(rows)}</ul></section>"


def _html_evidence(item: dict[str, Any]) -> str:
    if not item.get("evidence_snippet"):
        return ""
    return f"<p class=\"evidence\">Evidence: {html.escape(str(item['evidence_snippet']))}</p>"


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


def _exportable_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("review_status") != "rejected"]


def _effective_description(item: dict[str, Any]) -> str:
    return str(item.get("effective_description") or item.get("description") or "")


def _clean_review_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
