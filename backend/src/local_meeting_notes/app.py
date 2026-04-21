"""CLI entrypoint for the backend skeleton."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from .bootstrap import bootstrap_application
from .audio_capture.dependencies import AudioDependencyError
from .audio_capture.worker import run_capture_worker
from .audio_capture.service import AudioCaptureService
from .models import ActionRecord, DecisionRecord, SummaryRecord
from .storage.database import connection_context
from .storage.mock_seed import build_mock_records, build_mock_session
from .storage.repository import (
    insert_action,
    insert_decision,
    insert_meeting,
    insert_participant,
    insert_summary,
    insert_transcript_segment,
    update_meeting_status,
)
from .storage.session_state import clear_session_state, read_session_state, write_session_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-meeting-notes")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialise config, logging, and local folders.")

    db_parser = subparsers.add_parser("db", help="Database commands.")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)
    db_subparsers.add_parser("bootstrap", help="Create SQLite schema if needed.")

    session_parser = subparsers.add_parser("session", help="Mock meeting session commands.")
    session_subparsers = session_parser.add_subparsers(dest="session_command", required=True)

    session_start = session_subparsers.add_parser("start", help="Start a mock meeting session.")
    session_start.add_argument("--title", default="Mock Local Meeting")

    session_subparsers.add_parser("stop", help="Stop the current mock meeting session.")

    audio_parser = subparsers.add_parser("audio", help="Windows audio capture commands.")
    audio_subparsers = audio_parser.add_subparsers(dest="audio_command", required=True)

    audio_subparsers.add_parser("devices", help="List audio devices visible to the capture stack.")

    audio_start = audio_subparsers.add_parser("start", help="Start manual local audio capture.")
    audio_start.add_argument("--chunk-seconds", type=int)
    audio_start.add_argument("--sample-rate", type=int)
    audio_start.add_argument("--channels", type=int)
    audio_start.add_argument("--no-loopback", action="store_true")
    audio_start.add_argument("--no-microphone", action="store_true")

    audio_subparsers.add_parser("stop", help="Stop the active local audio capture session.")
    audio_subparsers.add_parser("status", help="Show the active audio capture state.")

    audio_worker = audio_subparsers.add_parser("worker", help=argparse.SUPPRESS)
    audio_worker.add_argument("--state-path", required=True)

    return parser


def run_init() -> int:
    state = bootstrap_application()
    state.logger.info("Initialised %s", state.config.app_name)
    print(f"Initialised {state.config.app_name}")
    print(f"Database path: {state.config.database_path}")
    return 0


def run_db_bootstrap() -> int:
    state = bootstrap_application(bootstrap_db=True)
    print(f"Bootstrapped SQLite schema at {state.config.database_path}")
    return 0


def run_session_start(title: str) -> int:
    state = bootstrap_application(bootstrap_db=True)
    session = build_mock_session(state.config.data_dir, title=title)
    records = build_mock_records(session)

    with connection_context(state.config.database_path) as connection:
        meeting_id = insert_meeting(connection, records["meeting"])

        for participant in records["participants"]:
            participant.meeting_id = meeting_id
            insert_participant(connection, participant)

        for segment in records["segments"]:
            segment.meeting_id = meeting_id
            insert_transcript_segment(connection, segment)

        summary = records["summary"]
        assert isinstance(summary, SummaryRecord)
        summary.meeting_id = meeting_id
        insert_summary(connection, summary)

        action = records["action"]
        assert isinstance(action, ActionRecord)
        action.meeting_id = meeting_id
        insert_action(connection, action)

        decision = records["decision"]
        assert isinstance(decision, DecisionRecord)
        decision.meeting_id = meeting_id
        insert_decision(connection, decision)

        connection.commit()

    write_session_state(str(state.config.session_state_path), session)
    state.logger.info("Started mock meeting session %s", session.meeting_id)
    print(f"Started mock meeting session: {session.meeting_id}")
    return 0


def run_session_stop() -> int:
    state = bootstrap_application(bootstrap_db=True)
    session_state = read_session_state(str(state.config.session_state_path))

    if session_state is None:
        print("No mock meeting session is currently active.")
        return 0

    ended_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    with connection_context(state.config.database_path) as connection:
        update_meeting_status(connection, session_state["meeting_id"], "stopped", ended_at=ended_at)
        connection.commit()

    clear_session_state(str(state.config.session_state_path))
    state.logger.info("Stopped mock meeting session %s", session_state["meeting_id"])
    print(f"Stopped mock meeting session: {session_state['meeting_id']}")
    return 0


def _get_audio_service() -> AudioCaptureService:
    state = bootstrap_application()
    service = state.services["audio_capture"]
    assert isinstance(service, AudioCaptureService)
    return service


def run_audio_devices() -> int:
    service = _get_audio_service()
    try:
        devices = service.list_devices()
    except AudioDependencyError as exc:
        print(str(exc))
        return 1

    if not devices:
        print("No audio devices were detected.")
        return 0

    for device in devices:
        default_marker = " (default)" if device.is_default else ""
        print(f"{device.kind}: {device.name}{default_marker}")
    return 0


def run_audio_start(
    *,
    chunk_seconds: int | None,
    sample_rate: int | None,
    channels: int | None,
    no_loopback: bool,
    no_microphone: bool,
) -> int:
    state = bootstrap_application()
    service = state.services["audio_capture"]
    assert isinstance(service, AudioCaptureService)
    try:
        capture_state = service.start_capture(
            include_loopback=not no_loopback,
            include_microphone=not no_microphone,
            chunk_seconds=chunk_seconds or state.config.audio_chunk_seconds,
            sample_rate=sample_rate or state.config.audio_sample_rate,
            channels=channels or state.config.audio_channels,
        )
    except (AudioDependencyError, RuntimeError) as exc:
        print(str(exc))
        return 1

    print(f"Started audio capture: {capture_state['capture_id']}")
    print(f"Output directory: {capture_state['output_dir']}")
    return 0


def run_audio_stop() -> int:
    service = _get_audio_service()
    state = service.stop_capture()
    print(f"Audio capture status: {state['status']}")
    if state.get("last_error"):
        print(f"Last error: {state['last_error']}")
    return 0


def run_audio_status() -> int:
    service = _get_audio_service()
    state = service.status()
    print(f"Audio capture status: {state['status']}")
    if state.get("capture_id"):
        print(f"Capture ID: {state['capture_id']}")
    if state.get("output_dir"):
        print(f"Output directory: {state['output_dir']}")
    if state.get("last_error"):
        print(f"Last error: {state['last_error']}")
    return 0


def run_audio_worker_entry(state_path: str) -> int:
    state = bootstrap_application()
    return run_capture_worker(state.config, Path(state_path))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return run_init()
    if args.command == "db" and args.db_command == "bootstrap":
        return run_db_bootstrap()
    if args.command == "session" and args.session_command == "start":
        return run_session_start(args.title)
    if args.command == "session" and args.session_command == "stop":
        return run_session_stop()
    if args.command == "audio" and args.audio_command == "devices":
        return run_audio_devices()
    if args.command == "audio" and args.audio_command == "start":
        return run_audio_start(
            chunk_seconds=args.chunk_seconds,
            sample_rate=args.sample_rate,
            channels=args.channels,
            no_loopback=args.no_loopback,
            no_microphone=args.no_microphone,
        )
    if args.command == "audio" and args.audio_command == "stop":
        return run_audio_stop()
    if args.command == "audio" and args.audio_command == "status":
        return run_audio_status()
    if args.command == "audio" and args.audio_command == "worker":
        return run_audio_worker_entry(args.state_path)

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
