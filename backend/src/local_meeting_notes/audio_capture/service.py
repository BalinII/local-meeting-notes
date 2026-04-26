"""Windows-oriented audio capture service for the MVP."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ..config import AppConfig
from .dependencies import AudioDependencyError, load_audio_dependencies
from .models import AudioCaptureSession, AudioDeviceInfo
from .state import read_capture_state, write_capture_state


def _utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class AudioCaptureService:
    startup_timeout_seconds = 8.0

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.audio_capture")

    def _get_loopback_microphone(self, soundcard_module):
        default_speaker = soundcard_module.default_speaker()
        speaker_id = getattr(default_speaker, "id", None)
        speaker_name = getattr(default_speaker, "name", "Unknown speaker")
        self.logger.info(
            "Resolving loopback capture device for default speaker: %s (%s)",
            speaker_name,
            speaker_id or "no-id",
        )

        if speaker_id:
            return soundcard_module.get_microphone(speaker_id, include_loopback=True)

        for microphone in soundcard_module.all_microphones(include_loopback=True):
            if speaker_name in getattr(microphone, "name", ""):
                return microphone

        raise RuntimeError(f"Could not resolve a loopback microphone for speaker '{speaker_name}'.")

    def list_devices(self) -> list[AudioDeviceInfo]:
        soundcard, _ = load_audio_dependencies()

        devices: list[AudioDeviceInfo] = []
        default_speaker = soundcard.default_speaker()
        default_microphone = soundcard.default_microphone()

        for speaker in soundcard.all_speakers():
            devices.append(
                AudioDeviceInfo(
                    kind="speaker",
                    name=speaker.name,
                    identifier=getattr(speaker, "id", speaker.name),
                    is_default=getattr(speaker, "id", speaker.name)
                    == getattr(default_speaker, "id", getattr(default_speaker, "name", None)),
                )
            )

        for microphone in soundcard.all_microphones(include_loopback=False):
            devices.append(
                AudioDeviceInfo(
                    kind="microphone",
                    name=microphone.name,
                    identifier=getattr(microphone, "id", microphone.name),
                    is_default=getattr(microphone, "id", microphone.name)
                    == getattr(default_microphone, "id", getattr(default_microphone, "name", None)),
                )
            )

        return devices

    def get_status(self) -> dict[str, object]:
        return read_capture_state(self.config.audio_capture_state_path) or {"status": "idle"}

    def _wait_for_startup_transition(
        self, process: subprocess.Popen[bytes], capture_id: str
    ) -> dict[str, object]:
        deadline = time.time() + self.startup_timeout_seconds

        while time.time() < deadline:
            state = self.get_status()
            if state.get("status") in {"running", "failed", "stopped"}:
                return state
            if process.poll() is not None:
                break
            time.sleep(0.2)

        state = self.get_status()
        if state.get("status") == "starting":
            state["status"] = "failed"
            state["last_error"] = (
                f"Audio startup timed out after {self.startup_timeout_seconds:.1f}s "
                f"for capture {capture_id}. Loopback startup may be blocked by an invalid "
                "loopback device, unsupported sample rate, or a Windows driver limitation."
            )
            state["failed_at"] = _utc_iso()
            write_capture_state(self.config.audio_capture_state_path, state)
            self.logger.error(state["last_error"])
        return state

    def start_capture(
        self,
        *,
        include_loopback: bool,
        include_microphone: bool,
        chunk_seconds: int,
        sample_rate: int,
        channels: int,
        capture_id: str | None = None,
    ) -> dict[str, object]:
        existing = self.get_status()
        if existing.get("status") in {"starting", "running"}:
            raise RuntimeError("Audio capture is already running.")

        if not include_loopback and not include_microphone:
            raise RuntimeError("At least one capture source must be enabled.")

        speaker_name: str | None = None
        microphone_name: str | None = None
        try:
            soundcard, _ = load_audio_dependencies()
            if include_loopback:
                loopback_device = self._get_loopback_microphone(soundcard)
                speaker_name = getattr(loopback_device, "name", "Unknown loopback")
                self.logger.info(
                    "Selected loopback device: %s (%s)",
                    speaker_name,
                    getattr(loopback_device, "id", "no-id"),
                )
            if include_microphone:
                microphone_name = getattr(soundcard.default_microphone(), "name", "Unknown microphone")
        except AudioDependencyError:
            raise

        capture_id = capture_id or f"capture-{uuid4().hex[:8]}"
        output_dir = self.config.audio_output_dir / capture_id
        stop_request_path = self.config.temp_output_dir / f"{capture_id}.stop"
        stop_request_path.unlink(missing_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        existing_chunk_files = [
            str(path)
            for path in sorted(output_dir.rglob("*.wav"))
        ]
        next_chunk_index = _next_chunk_index_from_files(existing_chunk_files)
        initial_started_at = (
            existing.get("initial_started_at")
            if existing.get("capture_id") == capture_id and existing.get("initial_started_at")
            else _utc_iso()
        )

        session = AudioCaptureSession(
            capture_id=capture_id,
            output_dir=output_dir,
            stop_request_path=stop_request_path,
            chunk_seconds=chunk_seconds,
            sample_rate=sample_rate,
            channels=channels,
            include_microphone=include_microphone,
            include_loopback=include_loopback,
            microphone_name=microphone_name,
            speaker_name=speaker_name,
            status="starting",
        )

        payload = {
            "capture_id": session.capture_id,
            "output_dir": str(session.output_dir),
            "stop_request_path": str(session.stop_request_path),
            "chunk_seconds": session.chunk_seconds,
            "sample_rate": session.sample_rate,
            "channels": session.channels,
            "include_microphone": session.include_microphone,
            "include_loopback": session.include_loopback,
            "microphone_name": session.microphone_name,
            "speaker_name": session.speaker_name,
            "status": session.status,
            "pid": None,
            "started_at": _utc_iso(),
            "initial_started_at": initial_started_at,
            "chunk_files": existing_chunk_files,
            "next_chunk_index": next_chunk_index,
            "last_error": None,
        }
        write_capture_state(self.config.audio_capture_state_path, payload)

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "local_meeting_notes.app",
                "audio",
                "worker",
                "--state-path",
                str(self.config.audio_capture_state_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        payload["pid"] = process.pid
        write_capture_state(self.config.audio_capture_state_path, payload)
        self.logger.info(
            "Started audio capture %s with pid=%s loopback=%s microphone=%s",
            capture_id,
            process.pid,
            include_loopback,
            include_microphone,
        )
        return self._wait_for_startup_transition(process, capture_id)

    def stop_capture(self, timeout_seconds: float = 10.0) -> dict[str, object]:
        state = read_capture_state(self.config.audio_capture_state_path)
        if state is None or state.get("status") not in {"starting", "running"}:
            return {"status": "idle", "message": "No active audio capture session."}

        stop_request_path = Path(state["stop_request_path"])
        stop_request_path.touch(exist_ok=True)
        self.logger.info("Stop requested for audio capture %s", state["capture_id"])

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            refreshed = read_capture_state(self.config.audio_capture_state_path)
            if refreshed is None:
                break
            if refreshed.get("status") in {"stopped", "failed"}:
                return refreshed
            time.sleep(0.25)

        refreshed = read_capture_state(self.config.audio_capture_state_path) or state
        refreshed["status"] = refreshed.get("status", "stopping")
        refreshed["stop_requested_at"] = _utc_iso()
        write_capture_state(self.config.audio_capture_state_path, refreshed)
        return refreshed

    def status(self) -> dict[str, object]:
        state = self.get_status()
        state.setdefault(
            "message",
            "Windows loopback capture is practical but fragile across devices and sample rates.",
        )
        if state.get("status") == "failed" and state.get("last_error"):
            state["message"] = f"{state['message']} Failure: {state['last_error']}"
        return state


def _next_chunk_index_from_files(paths: list[str]) -> int:
    next_index = 1
    for raw_path in paths:
        stem = Path(raw_path).stem
        prefix = stem.split("_", 1)[0]
        if prefix.isdigit():
            next_index = max(next_index, int(prefix) + 1)
    return next_index
