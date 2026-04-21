"""Models for Windows audio capture state and device metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AudioDeviceInfo:
    kind: str
    name: str
    identifier: str
    is_default: bool = False


@dataclass(slots=True)
class AudioCaptureSession:
    capture_id: str
    output_dir: Path
    stop_request_path: Path
    chunk_seconds: int
    sample_rate: int
    channels: int
    include_microphone: bool
    include_loopback: bool
    microphone_name: str | None = None
    speaker_name: str | None = None
    status: str = "starting"
    pid: int | None = None
    last_error: str | None = None
    chunk_files: list[str] = field(default_factory=list)
