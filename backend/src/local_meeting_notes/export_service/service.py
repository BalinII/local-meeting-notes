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
)


EXPORT_FORMATS = {"markdown", "html", "json"}


class ExportService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_review_payload(self, capture_id: str) -> dict[str, Any]:
        bootstrap_database(self.config)
        with connection_context(self.config.database_path) as connection:
            summaries = [dict(row) for row in fetch_summaries_for_capture(connection, capture_id)]
            actions = [dict(row) for row in fetch_actions_for_capture(connection, capture_id)]
            decisions = [dict(row) for row in fetch_decisions_for_capture(connection, capture_id)]
            follow_ups = [dict(row) for row in fetch_follow_ups_for_capture(connection, capture_id)]

        blockers_risks = [item for item in follow_ups if item["follow_up_type"] == "blocker_risk"]
        open_questions = [item for item in follow_ups if item["follow_up_type"] == "open_question"]
        other_follow_ups = [item for item in follow_ups if item["follow_up_type"] == "follow_up"]

        providers = sorted(
            {
                str(item["provider_name"])
                for collection in (summaries, actions, decisions, follow_ups)
                for item in collection
                if item.get("provider_name")
            }
        )
        generated_values = [
            str(item["generated_at"])
            for collection in (summaries, actions, decisions, follow_ups)
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
    .evidence {{ color: #5b6678; font-size: 0.92em; }}
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
            lines.extend([f"> Evidence: {summary['evidence_snippet']}", ""])
    return lines


def _markdown_items(
    title: str, items: list[dict[str, Any]], *, include_owner: bool = False
) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        return lines + [f"No {title.lower()} found.", ""]
    for item in items:
        owner = f" [{_owner_label(item)}]" if include_owner else ""
        lines.append(f"- {item['description']}{owner}")
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
    if not items:
        return f"<section><h2>{html.escape(title)}</h2><p>No {html.escape(title.lower())} found.</p></section>"
    rows = []
    for item in items:
        owner = f" <span class=\"badge\">{html.escape(_owner_label(item))}</span>" if include_owner else ""
        timing = ""
        if item.get("start_offset_seconds") is not None:
            timing = f"<p class=\"evidence\">Time: {item['start_offset_seconds']}-{item['end_offset_seconds']}s</p>"
        rows.append(
            f"<li><strong>{html.escape(str(item['description']))}</strong>{owner}"
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
    owner = item.get("owner_name") or "Unconfirmed speaker"
    if owner in {"Unknown", "Unconfirmed speaker"}:
        return f"{owner} - review ownership"
    return str(owner)


def _now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
