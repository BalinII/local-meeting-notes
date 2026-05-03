from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from local_meeting_notes.audio_capture.service import _next_chunk_index_from_files
from local_meeting_notes.audio_capture.state import read_capture_state, write_capture_state
from local_meeting_notes.audio_capture.worker import _record_source


def _build_state(state_path: Path, output_dir: Path, stop_path: Path) -> None:
    write_capture_state(
        state_path,
        {
            "capture_id": "capture-test",
            "output_dir": str(output_dir),
            "stop_request_path": str(stop_path),
            "chunk_seconds": 2,
            "sample_rate": 4,
            "channels": 1,
            "include_microphone": True,
            "include_loopback": False,
            "status": "running",
            "pid": 123,
            "chunk_files": [],
            "next_chunk_index": 1,
        },
    )


def test_record_source_checks_stop_between_small_reads_and_flushes_partial(tmp_path) -> None:
    state_path = tmp_path / "state.json"
    output_dir = tmp_path / "audio" / "microphone"
    stop_path = tmp_path / "stop.flag"
    _build_state(state_path, output_dir, stop_path)

    writes: list[tuple[str, np.ndarray, int]] = []
    read_calls: list[int] = []

    class DummyRecorder:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def record(self, numframes: int):
            read_calls.append(numframes)
            if len(read_calls) == 3:
                stop_path.touch(exist_ok=True)
            return np.arange(numframes, dtype=np.float32)

    class DummySoundfile:
        @staticmethod
        def write(path, frames, sample_rate):
            writes.append((path, np.asarray(frames), sample_rate))

    _record_source(
        source_name="microphone",
        recorder_factory=lambda **_: DummyRecorder(),
        output_dir=output_dir,
        sample_rate=4,
        channels=1,
        chunk_seconds=2,
        stop_path=stop_path,
        soundfile_module=DummySoundfile(),
        logger=type("L", (), {"info": lambda *args, **kwargs: None})(),
        state_path=state_path,
        startup_event=threading.Event(),
        state_lock=threading.Lock(),
    )

    # 0.5s read window at 4Hz => 2 frames per read.
    assert read_calls == [2, 2, 2]
    # 3 reads = 6 frames total => one full 8-frame chunk isn't possible, so partial flush writes one chunk.
    assert len(writes) == 1
    assert writes[0][1].shape[0] == 6

    state = read_capture_state(state_path)
    assert state is not None
    assert [Path(p).name for p in state["chunk_files"]] == [Path(writes[0][0]).name]


def test_record_source_chunk_files_are_appended_in_order(tmp_path) -> None:
    state_path = tmp_path / "state.json"
    output_dir = tmp_path / "audio" / "microphone"
    stop_path = tmp_path / "stop.flag"
    _build_state(state_path, output_dir, stop_path)

    class DummyRecorder:
        calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def record(self, numframes: int):
            self.calls += 1
            if self.calls == 7:
                stop_path.touch(exist_ok=True)
            return np.ones((numframes,), dtype=np.float32)

    class DummySoundfile:
        @staticmethod
        def write(path, frames, sample_rate):
            pass

    _record_source(
        source_name="microphone",
        recorder_factory=lambda **_: DummyRecorder(),
        output_dir=output_dir,
        sample_rate=4,
        channels=1,
        chunk_seconds=2,
        stop_path=stop_path,
        soundfile_module=DummySoundfile(),
        logger=type("L", (), {"info": lambda *args, **kwargs: None})(),
        state_path=state_path,
        startup_event=threading.Event(),
        state_lock=threading.Lock(),
    )

    state = read_capture_state(state_path)
    assert state is not None
    names = [Path(p).name for p in state["chunk_files"]]
    assert names == sorted(names)
    assert names[0].startswith("000001_")
    assert names[1].startswith("000002_")


def test_next_chunk_index_from_files_unchanged() -> None:
    assert _next_chunk_index_from_files([
        "audio/microphone/000002_time_microphone.wav",
        "audio/microphone/not-a-chunk.wav",
        "audio/microphone/000010_time_microphone.wav",
    ]) == 11


def test_record_source_updates_health_with_levels(tmp_path) -> None:
    state_path = tmp_path / "state.json"
    output_dir = tmp_path / "audio" / "microphone"
    stop_path = tmp_path / "stop.flag"
    _build_state(state_path, output_dir, stop_path)
    state = read_capture_state(state_path)
    assert state is not None
    state["health"] = {
        "updated_at": "0",
        "sources": {"microphone": {"enabled": True, "stream_open": False, "is_silent": True}},
    }
    write_capture_state(state_path, state)

    class DummyRecorder:
        calls = 0
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def record(self, numframes: int):
            self.calls += 1
            if self.calls == 2:
                stop_path.touch(exist_ok=True)
            return np.full((numframes,), 0.25, dtype=np.float32)

    class DummySoundfile:
        @staticmethod
        def write(path, frames, sample_rate): pass

    _record_source(
        source_name="microphone",
        recorder_factory=lambda **_: DummyRecorder(),
        output_dir=output_dir,
        sample_rate=4,
        channels=1,
        chunk_seconds=8,
        stop_path=stop_path,
        soundfile_module=DummySoundfile(),
        logger=type("L", (), {"info": lambda *args, **kwargs: None})(),
        state_path=state_path,
        startup_event=threading.Event(),
        state_lock=threading.Lock(),
    )
    health = read_capture_state(state_path)["health"]["sources"]["microphone"]
    assert health["stream_open"] is True
    assert health["recent_rms"] > 0
    assert health["recent_peak"] > 0
    assert health["is_silent"] is False


def test_record_source_sets_silent_warning(tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "state.json"
    output_dir = tmp_path / "audio" / "loopback"
    stop_path = tmp_path / "stop.flag"
    _build_state(state_path, output_dir, stop_path)
    state = read_capture_state(state_path)
    assert state is not None
    state["include_microphone"] = False
    state["include_loopback"] = True
    state["health"] = {"updated_at": "0", "sources": {"loopback": {"enabled": True, "stream_open": False, "is_silent": True}}}
    write_capture_state(state_path, state)
    ticks = iter([0.0, 0.0, 0.0, 6.5, 6.5, 6.5, 6.5])
    monkeypatch.setattr("local_meeting_notes.audio_capture.worker.time.monotonic", lambda: next(ticks))

    class DummyRecorder:
        calls = 0
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def record(self, numframes: int):
            self.calls += 1
            if self.calls == 2:
                stop_path.touch(exist_ok=True)
            return np.zeros((numframes,), dtype=np.float32)

    class DummySoundfile:
        @staticmethod
        def write(path, frames, sample_rate): pass

    _record_source(
        source_name="loopback",
        recorder_factory=lambda **_: DummyRecorder(),
        output_dir=output_dir,
        sample_rate=4,
        channels=1,
        chunk_seconds=5,
        stop_path=stop_path,
        soundfile_module=DummySoundfile(),
        logger=type("L", (), {"info": lambda *args, **kwargs: None})(),
        state_path=state_path,
        startup_event=threading.Event(),
        state_lock=threading.Lock(),
    )
    warning = read_capture_state(state_path)["health"]["sources"]["loopback"]["warning"]
    assert "No meaningful loopback audio detected recently" in warning
