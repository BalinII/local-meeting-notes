"""State persistence for manual audio capture sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_capture_state(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def write_capture_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_capture_state(path: Path) -> None:
    path.unlink(missing_ok=True)
