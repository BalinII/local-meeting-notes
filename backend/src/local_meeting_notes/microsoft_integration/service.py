"""Minimal read-only Microsoft calendar integration for upcoming meetings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import AppConfig
from ..utils.placeholders import PlaceholderStatus


@dataclass(slots=True)
class CalendarReadResult:
    meetings: list[dict[str, object]]
    available: bool
    message: str
    provider: str | None = None


class MicrosoftIntegrationService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> PlaceholderStatus:
        return PlaceholderStatus(
            component="microsoft_integration",
            message="Reserved for optional metadata integration only; auth is not implemented here.",
        )

    def list_upcoming_meetings(self, *, limit: int = 20) -> CalendarReadResult:
        provider = (self.config.calendar_provider or "none").strip().lower()
        if provider != "microsoft_graph":
            return CalendarReadResult(
                meetings=[],
                available=False,
                message="Live calendar is disabled. Configure CALENDAR_PROVIDER=microsoft_graph to enable read-only upcoming meetings.",
            )
        token = (self.config.microsoft_graph_access_token or "").strip()
        if not token:
            return CalendarReadResult(
                meetings=[],
                available=False,
                message="Live calendar is configured but unavailable because MICROSOFT_GRAPH_ACCESS_TOKEN is not set.",
                provider="microsoft_graph",
            )
        return self._list_upcoming_from_graph(token=token, limit=limit)

    def _list_upcoming_from_graph(self, *, token: str, limit: int) -> CalendarReadResult:
        now = datetime.now(UTC).replace(microsecond=0)
        lookahead = now + timedelta(hours=max(1, self.config.calendar_lookahead_hours))
        params = {
            "$select": "id,subject,start,onlineMeetingUrl,webLink,isCancelled,lastModifiedDateTime",
            "$orderby": "start/dateTime",
            "$top": str(max(1, min(int(limit), 50))),
            "$filter": f"start/dateTime ge '{now.isoformat()}' and start/dateTime le '{lookahead.isoformat()}' and isCancelled eq false",
        }
        url = f"{self.config.microsoft_graph_base_url.rstrip('/')}/me/events?{urlencode(params)}"
        request = Request(
            url=url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError) as exc:
            return CalendarReadResult(
                meetings=[],
                available=False,
                message=f"Live calendar access failed; continuing with manual planning ({exc.__class__.__name__}).",
                provider="microsoft_graph",
            )

        items = payload.get("value") or []
        meetings = []
        for row in items:
            subject = str(row.get("subject") or "").strip()
            event_id = str(row.get("id") or "").strip()
            if not subject or not event_id:
                continue
            start = row.get("start") or {}
            start_raw = str(start.get("dateTime") or "").strip()
            start_tz = str(start.get("timeZone") or "UTC").strip()
            planned_start_at = _normalize_graph_start(start_raw, start_tz)
            meetings.append(
                {
                    "external_meeting_id": f"msgraph:{event_id}",
                    "title": subject,
                    "planned_start_at": planned_start_at,
                    "imported_metadata_json": json.dumps(
                        {
                            "provider": "microsoft_graph",
                            "web_link": row.get("webLink"),
                            "online_meeting_url": row.get("onlineMeetingUrl"),
                            "last_modified_at": row.get("lastModifiedDateTime"),
                        },
                        ensure_ascii=False,
                    ),
                }
            )
        return CalendarReadResult(
            meetings=meetings,
            available=True,
            message="Live upcoming meetings loaded from Microsoft 365 calendar.",
            provider="microsoft_graph",
        )


def _normalize_graph_start(date_time_value: str, timezone_value: str) -> str | None:
    if not date_time_value:
        return None
    try:
        parsed = datetime.fromisoformat(date_time_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).replace(microsecond=0).isoformat()
    except ValueError:
        return f"{date_time_value} ({timezone_value or 'Unknown TZ'})"
