"""Background worker for chunked local audio capture."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from ..config import AppConfig
from ..logging_config import configure_logging
from .dependencies import AudioDependencyError, load_audio_dependencies
from .state import read_capture_state, write_capture_state


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _normalise_channels(frames, channels: int):
    if channels == 1 and getattr(frames, "ndim", 1) > 1:
        return frames.mean(axis=1)
    return frames


def _record_source(
    *,
    source_name: str,
    recorder_factory,
    output_dir: Path,
    sample_rate: int,
    channels: int,
    chunk_seconds: int,
    stop_path: Path,
    soundfile_module,
    logger,
    state_path: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_frames = sample_rate * chunk_seconds

    with recorder_factory(samplerate=sample_rate, channels=channels) as recorder:
        while not stop_path.exists():
            frames = recorder.record(numframes=chunk_frames)
            frames = _normalise_channels(frames, channels)
            chunk_path = output_dir / f"{source_name}_{_utc_timestamp()}.wav"
            soundfile_module.write(str(chunk_path), frames, sample_rate)
            logger.info("Wrote %s chunk to %s", source_name, chunk_path)

            state = read_capture_state(state_path)
            if state is not None:
                chunk_files = list(state.get("chunk_files", []))
                chunk_files.append(str(chunk_path))
                state["chunk_files"] = chunk_files
                state["last_chunk_at"] = _utc_timestamp()
                write_capture_state(state_path, state)


def run_capture_worker(config: AppConfig, state_path: Path) -> int:
    logger = configure_logging(config)
    state = read_capture_state(state_path)

    if state is None:
        logger.error("Capture worker started without state file.")
        return 1

    try:
        soundcard, soundfile = load_audio_dependencies()
    except AudioDependencyError as exc:
        state["status"] = "failed"
        state["last_error"] = str(exc)
        write_capture_state(state_path, state)
        logger.exception("Audio capture dependencies are unavailable.")
        return 1

    stop_path = Path(state["stop_request_path"])
    sample_rate = int(state["sample_rate"])
    channels = int(state["channels"])
    chunk_seconds = int(state["chunk_seconds"])
    threads: list[threading.Thread] = []
    failures: list[str] = []
    lock = threading.Lock()

    def run_source(name: str, recorder_factory, source_dir: Path) -> None:
        try:
            _record_source(
                source_name=name,
                recorder_factory=recorder_factory,
                output_dir=source_dir,
                sample_rate=sample_rate,
                channels=channels,
                chunk_seconds=chunk_seconds,
                stop_path=stop_path,
                soundfile_module=soundfile,
                logger=logger,
                state_path=state_path,
            )
        except Exception as exc:  # pragma: no cover - exercised only with hardware
            with lock:
                failures.append(f"{name}: {exc}")
            stop_path.touch(exist_ok=True)
            logger.exception("Audio capture failed for %s", name)

    if state.get("include_loopback"):
        speaker = soundcard.default_speaker()
        logger.info("Selected system loopback device: %s", speaker.name)
        threads.append(
            threading.Thread(
                target=run_source,
                kwargs={
                    "name": "loopback",
                    "recorder_factory": speaker.recorder,
                    "source_dir": Path(state["output_dir"]) / "loopback",
                },
                daemon=True,
            )
        )

    if state.get("include_microphone"):
        microphone = soundcard.default_microphone()
        logger.info("Selected microphone device: %s", microphone.name)
        threads.append(
            threading.Thread(
                target=run_source,
                kwargs={
                    "name": "microphone",
                    "recorder_factory": microphone.recorder,
                    "source_dir": Path(state["output_dir"]) / "microphone",
                },
                daemon=True,
            )
        )

    if not threads:
        state["status"] = "failed"
        state["last_error"] = "No capture sources were enabled."
        write_capture_state(state_path, state)
        logger.error("No capture sources are enabled.")
        return 1

    state["status"] = "running"
    state["pid"] = state.get("pid")
    write_capture_state(state_path, state)
    logger.info(
        "Audio capture worker started with loopback=%s microphone=%s chunk_seconds=%s",
        state.get("include_loopback"),
        state.get("include_microphone"),
        chunk_seconds,
    )

    for thread in threads:
        thread.start()

    while any(thread.is_alive() for thread in threads):
        time.sleep(0.25)

    state = read_capture_state(state_path) or state
    state["status"] = "failed" if failures else "stopped"
    state["stopped_at"] = _utc_timestamp()
    state["last_error"] = "; ".join(failures) if failures else None
    write_capture_state(state_path, state)
    logger.info("Audio capture worker stopped with status=%s", state["status"])
    return 0 if not failures else 1
