"""CLI entrypoint for the backend skeleton."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from .bootstrap import bootstrap_application
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

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
