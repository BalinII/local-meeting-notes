"""Filesystem state for the current mock session."""

from __future__ import annotations

import json
from dataclasses import asdict

from ..models import MeetingSession


def write_session_state(path: str, session: MeetingSession) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        payload = asdict(session)
        payload["workspace_dir"] = str(session.workspace_dir)
        json.dump(payload, handle, indent=2)


def read_session_state(path: str) -> dict[str, str] | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def clear_session_state(path: str) -> None:
    from pathlib import Path

    Path(path).unlink(missing_ok=True)
