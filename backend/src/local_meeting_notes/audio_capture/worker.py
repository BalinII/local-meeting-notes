"""Background worker for chunked local audio capture."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from traceback import format_exc

import numpy as np

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


def _update_capture_state(state_path: Path, **updates) -> dict[str, object] | None:
    state = read_capture_state(state_path)
    if state is None:
        return None
    state.update(updates)
    write_capture_state(state_path, state)
    return state


def _reserve_chunk_path(
    *,
    state_path: Path,
    source_dir: Path,
    source_name: str,
    state_lock: threading.Lock,
) -> Path:
    with state_lock:
        state = read_capture_state(state_path)
        if state is None:
            raise RuntimeError("Capture state disappeared while reserving a chunk path.")
        next_index = int(state.get("next_chunk_index", 1))
        chunk_path = source_dir / f"{next_index:06d}_{_utc_timestamp()}_{source_name}.wav"
        state["next_chunk_index"] = next_index + 1
        write_capture_state(state_path, state)
    return chunk_path


def _append_chunk_state(
    *,
    state_path: Path,
    chunk_path: Path,
    state_lock: threading.Lock,
) -> None:
    with state_lock:
        state = read_capture_state(state_path)
        if state is None:
            return
        chunk_files = list(state.get("chunk_files", []))
        chunk_files.append(str(chunk_path))
        state["chunk_files"] = chunk_files
        state["last_chunk_at"] = _utc_timestamp()
        write_capture_state(state_path, state)


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
    startup_event: threading.Event,
    state_lock: threading.Lock,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_frames = sample_rate * chunk_seconds
    read_window_seconds = 0.5
    read_frames = max(1, int(sample_rate * read_window_seconds))
    buffered_frames = None

    logger.info(
        "Opening %s stream with samplerate=%s channels=%s chunk_seconds=%s",
        source_name,
        sample_rate,
        channels,
        chunk_seconds,
    )
    logger.info(
        "%s using read window %.2fs (%s frames)",
        source_name,
        read_window_seconds,
        read_frames,
    )

    with recorder_factory(samplerate=sample_rate, channels=channels) as recorder:
        logger.info("%s stream opened successfully", source_name)
        while True:
            if stop_path.exists():
                break

            frames = recorder.record(numframes=read_frames)
            frames = _normalise_channels(frames, channels)
            if buffered_frames is None:
                logger.info("%s first frame read succeeded", source_name)
                startup_event.set()
                buffered_frames = frames
            else:
                buffered_frames = np.concatenate((buffered_frames, frames), axis=0)

            while len(buffered_frames) >= chunk_frames:
                chunk_payload = buffered_frames[:chunk_frames]
                buffered_frames = buffered_frames[chunk_frames:]
                chunk_path = _reserve_chunk_path(
                    state_path=state_path,
                    source_dir=output_dir,
                    source_name=source_name,
                    state_lock=state_lock,
                )
                soundfile_module.write(str(chunk_path), chunk_payload, sample_rate)
                logger.info("Wrote %s chunk to %s", source_name, chunk_path)
                _append_chunk_state(
                    state_path=state_path,
                    chunk_path=chunk_path,
                    state_lock=state_lock,
                )

        if buffered_frames is not None and len(buffered_frames) > 0:
            logger.info(
                "Flushing partial %s chunk with %s frames after stop request",
                source_name,
                len(buffered_frames),
            )
            chunk_path = _reserve_chunk_path(
                state_path=state_path,
                source_dir=output_dir,
                source_name=source_name,
                state_lock=state_lock,
            )
            soundfile_module.write(str(chunk_path), buffered_frames, sample_rate)
            logger.info("Wrote %s chunk to %s", source_name, chunk_path)
            _append_chunk_state(
                state_path=state_path,
                chunk_path=chunk_path,
                state_lock=state_lock,
            )


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
    state_lock = threading.Lock()
    startup_events: dict[str, threading.Event] = {}
    startup_timeout_seconds = 5.0

    def run_source(name: str, recorder_factory, source_dir: Path, startup_event: threading.Event) -> None:
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
                startup_event=startup_event,
                state_lock=state_lock,
            )
        except Exception as exc:  # pragma: no cover - exercised only with hardware
            with lock:
                failures.append(f"{name}: {exc}")
            _update_capture_state(
                state_path,
                status="failed",
                last_error=f"{name} startup failed: {exc}",
                failed_at=_utc_timestamp(),
            )
            stop_path.touch(exist_ok=True)
            logger.error("Audio capture failed for %s: %s", name, exc)
            logger.debug("Detailed %s failure:\n%s", name, format_exc())

    if state.get("include_loopback"):
        speaker = soundcard.default_speaker()
        loopback_microphone = soundcard.get_microphone(
            getattr(speaker, "id", speaker.name), include_loopback=True
        )
        logger.info(
            "Selected system loopback device: %s (%s)",
            getattr(loopback_microphone, "name", "Unknown loopback"),
            getattr(loopback_microphone, "id", "no-id"),
        )
        startup_events["loopback"] = threading.Event()
        threads.append(
            threading.Thread(
                target=run_source,
                kwargs={
                    "name": "loopback",
                    "recorder_factory": loopback_microphone.recorder,
                    "source_dir": Path(state["output_dir"]) / "loopback",
                    "startup_event": startup_events["loopback"],
                },
                daemon=True,
            )
        )

    if state.get("include_microphone"):
        microphone = soundcard.default_microphone()
        logger.info("Selected microphone device: %s", microphone.name)
        startup_events["microphone"] = threading.Event()
        threads.append(
            threading.Thread(
                target=run_source,
                kwargs={
                    "name": "microphone",
                    "recorder_factory": microphone.recorder,
                    "source_dir": Path(state["output_dir"]) / "microphone",
                    "startup_event": startup_events["microphone"],
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

    state["status"] = "starting"
    state["pid"] = state.get("pid")
    write_capture_state(state_path, state)
    logger.info(
        "Audio capture worker starting with loopback=%s microphone=%s chunk_seconds=%s",
        state.get("include_loopback"),
        state.get("include_microphone"),
        chunk_seconds,
    )

    for thread in threads:
        thread.start()

    startup_deadline = time.time() + startup_timeout_seconds
    required_sources = [name for name in ("loopback", "microphone") if name in startup_events]
    while time.time() < startup_deadline:
        if failures:
            break
        if all(startup_events[name].is_set() for name in required_sources):
            _update_capture_state(
                state_path,
                status="running",
                running_at=_utc_timestamp(),
                last_error=None,
            )
            logger.info("Audio capture worker transitioned to running")
            break
        time.sleep(0.1)
    else:
        missing = [name for name in required_sources if not startup_events[name].is_set()]
        reason = (
            f"Startup timeout after {startup_timeout_seconds:.1f}s waiting for: {', '.join(missing)}"
        )
        _update_capture_state(
            state_path,
            status="failed",
            last_error=reason,
            failed_at=_utc_timestamp(),
        )
        logger.error(reason)
        stop_path.touch(exist_ok=True)
        failures.append(reason)

    while any(thread.is_alive() for thread in threads):
        time.sleep(0.25)

    state = read_capture_state(state_path) or state
    if state.get("status") != "failed":
        state["status"] = "failed" if failures else "stopped"
    state["stopped_at"] = _utc_timestamp()
    if failures:
        state["last_error"] = "; ".join(failures)
    write_capture_state(state_path, state)
    logger.info("Audio capture worker stopped with status=%s", state["status"])
    return 0 if not failures else 1
