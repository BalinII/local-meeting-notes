"""CLI entrypoint for the backend skeleton."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .bootstrap import bootstrap_application
from .audio_capture.dependencies import AudioDependencyError
from .audio_capture.worker import run_capture_worker
from .audio_capture.service import AudioCaptureService
from .diarization_engine.service import DiarizationEngineService
from .export_service.service import EXPORT_FORMATS, ExportService
from .local_llm import LocalLlmClientError, build_local_llm_client
from .models import ActionRecord, DecisionRecord, SummaryRecord
from .summarizer.service import SummarizerService
from .action_extractor.service import ActionExtractorService
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
from .session_workflow.service import SessionWorkflowService
from .transcription_engine.providers import TranscriptionDependencyError
from .transcription_engine.service import TranscriptionEngineService


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
    session_subparsers.add_parser("list", help="List recent persisted recording sessions.")
    session_create = session_subparsers.add_parser("create", help="Create a new recording session.")
    session_create.add_argument("--title")
    session_get = session_subparsers.add_parser("get", help="Get a persisted recording session.")
    session_get.add_argument("--capture-id", required=True)
    session_rename = session_subparsers.add_parser("rename", help="Update the display name for a session.")
    session_rename.add_argument("--capture-id", required=True)
    session_rename.add_argument("--title", required=True)
    session_record_start = session_subparsers.add_parser("record-start", help="Start recording for a session.")
    session_record_start.add_argument("--capture-id", required=True)
    session_record_start.add_argument("--no-loopback", action="store_true")
    session_record_start.add_argument("--no-microphone", action="store_true")
    session_pause = session_subparsers.add_parser("pause", help="Pause recording for a session.")
    session_pause.add_argument("--capture-id", required=True)
    session_resume = session_subparsers.add_parser("resume", help="Resume recording for a session.")
    session_resume.add_argument("--capture-id", required=True)
    session_resume.add_argument("--no-loopback", action="store_true")
    session_resume.add_argument("--no-microphone", action="store_true")
    session_record_stop = session_subparsers.add_parser("record-stop", help="Stop a session and process outputs.")
    session_record_stop.add_argument("--capture-id", required=True)
    session_keep_audio = session_subparsers.add_parser("keep-audio", help="Set keep-source-audio for a session.")
    session_keep_audio.add_argument("--capture-id", required=True)
    session_keep_audio.add_argument("--enabled", choices=("true", "false"), required=True)
    session_delete_audio = session_subparsers.add_parser("delete-audio", help="Delete stored source audio for a session.")
    session_delete_audio.add_argument("--capture-id", required=True)
    session_archive = session_subparsers.add_parser("archive", help="Archive a session.")
    session_archive.add_argument("--capture-id", required=True)
    session_subparsers.add_parser("retention-show", help="Show persisted retention settings.")
    session_retention_update = session_subparsers.add_parser("retention-update", help="Update retention settings.")
    session_retention_update.add_argument("--raw-audio-retention-days", type=int, required=True)
    session_retention_update.add_argument("--delete-temp-processing-files", choices=("true", "false"), required=True)
    session_subparsers.add_parser("cleanup", help="Run source-audio and temp-file cleanup.")

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

    transcript_parser = subparsers.add_parser("transcript", help="Local transcription commands.")
    transcript_subparsers = transcript_parser.add_subparsers(dest="transcript_command", required=True)

    transcript_transcribe = transcript_subparsers.add_parser(
        "transcribe", help="Batch transcribe a capture by capture id."
    )
    transcript_transcribe.add_argument("--capture-id", required=True)

    transcript_status = transcript_subparsers.add_parser(
        "status", help="Show transcription status for a capture."
    )
    transcript_status.add_argument("--capture-id", required=True)

    transcript_list = transcript_subparsers.add_parser(
        "list", help="List transcript segments for a capture."
    )
    transcript_list.add_argument("--capture-id", required=True)

    diarize_parser = subparsers.add_parser("diarize", help="Local diarization commands.")
    diarize_subparsers = diarize_parser.add_subparsers(dest="diarize_command", required=True)

    diarize_run = diarize_subparsers.add_parser("run", help="Batch diarize a capture by capture id.")
    diarize_run.add_argument("--capture-id", required=True)

    diarize_status = diarize_subparsers.add_parser(
        "status", help="Show diarization status for a capture."
    )
    diarize_status.add_argument("--capture-id", required=True)

    diarize_list = diarize_subparsers.add_parser(
        "list", help="List diarization segments for a capture."
    )
    diarize_list.add_argument("--capture-id", required=True)

    summary_parser = subparsers.add_parser("summary", help="Summary generation commands.")
    summary_subparsers = summary_parser.add_subparsers(dest="summary_command", required=True)

    summary_generate = summary_subparsers.add_parser(
        "generate", help="Generate summaries for a capture."
    )
    summary_generate.add_argument("--capture-id", required=True)
    summary_generate.add_argument("--provider", choices=("heuristic", "local_llm"))

    summary_show = summary_subparsers.add_parser("show", help="Show summaries for a capture.")
    summary_show.add_argument("--capture-id", required=True)

    actions_parser = subparsers.add_parser("actions", help="Action extraction commands.")
    actions_subparsers = actions_parser.add_subparsers(dest="actions_command", required=True)

    actions_extract = actions_subparsers.add_parser(
        "extract", help="Extract actions, decisions, and follow-ups for a capture."
    )
    actions_extract.add_argument("--capture-id", required=True)
    actions_extract.add_argument("--provider", choices=("heuristic", "local_llm"))

    actions_list = actions_subparsers.add_parser(
        "list", help="List extracted actions, decisions, and follow-ups for a capture."
    )
    actions_list.add_argument("--capture-id", required=True)

    llm_parser = subparsers.add_parser("llm", help="Local LLM runtime commands.")
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command", required=True)
    llm_subparsers.add_parser("check", help="Check whether the local LLM runtime is reachable.")

    review_parser = subparsers.add_parser("review", help="Review persisted meeting-note outputs.")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)
    review_show = review_subparsers.add_parser("show", help="Show a review payload for a capture.")
    review_show.add_argument("--capture-id", required=True)
    review_show.add_argument("--format", choices=("json", "markdown"), default="json")
    review_recent = review_subparsers.add_parser(
        "recent", help="List recent captures with review metadata."
    )
    review_recent.add_argument("--limit", type=int, default=12)
    review_update = review_subparsers.add_parser(
        "update-item", help="Save review state for an extracted item."
    )
    review_update.add_argument("--item-type", choices=("action", "decision", "follow_up"), required=True)
    review_update.add_argument("--item-id", type=int, required=True)
    review_update.add_argument(
        "--review-status", choices=("generated", "accepted", "edited", "rejected"), required=True
    )
    review_update.add_argument("--description")
    review_update.add_argument("--owner-name")

    export_parser = subparsers.add_parser("export", help="Export meeting-note outputs.")
    export_subparsers = export_parser.add_subparsers(dest="export_command", required=True)
    export_run = export_subparsers.add_parser("run", help="Export a capture to markdown, HTML, or JSON.")
    export_run.add_argument("--capture-id", required=True)
    export_run.add_argument("--format", choices=tuple(sorted(EXPORT_FORMATS)), required=True)

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


def _get_transcription_service() -> TranscriptionEngineService:
    state = bootstrap_application(bootstrap_db=True)
    service = state.services["transcription_engine"]
    assert isinstance(service, TranscriptionEngineService)
    return service


def run_transcript_transcribe(capture_id: str) -> int:
    service = _get_transcription_service()
    try:
        result = service.transcribe_capture(capture_id)
    except (RuntimeError, TranscriptionDependencyError) as exc:
        print(str(exc))
        return 1

    print(f"Capture: {result['capture_id']}")
    print(f"Total chunks: {result['total_chunks']}")
    print(f"Completed chunks: {result['completed_chunks']}")
    print(f"Failed chunks: {result['failed_chunks']}")
    return 0


def run_transcript_status(capture_id: str) -> int:
    service = _get_transcription_service()
    status = service.get_status(capture_id)
    print(f"Capture: {status['capture_id']}")
    print(f"Status: {status['status']}")
    print(f"Total segments: {status['total_segments']}")
    print(f"Completed segments: {status['completed_segments']}")
    print(f"Failed segments: {status['failed_segments']}")
    if "pending_segments" in status:
        print(f"Pending segments: {status['pending_segments']}")
    return 0


def run_transcript_list(capture_id: str) -> int:
    service = _get_transcription_service()
    segments = service.list_segments(capture_id)
    if not segments:
        print(f"No transcript segments found for capture: {capture_id}")
        return 0

    for segment in segments:
        print(
            f"[{segment['transcription_status']}] "
            f"{segment['speaker_label']} "
            f"{segment['start_offset_seconds']}-{segment['end_offset_seconds']}s "
            f"{segment['source_chunk_path']}"
        )
        if segment["content"]:
            print(segment["content"])
        if segment["error_message"]:
            print(f"Error: {segment['error_message']}")
    return 0


def _get_diarization_service() -> DiarizationEngineService:
    state = bootstrap_application(bootstrap_db=True)
    service = state.services["diarization_engine"]
    assert isinstance(service, DiarizationEngineService)
    return service


def run_diarize_run(capture_id: str) -> int:
    service = _get_diarization_service()
    try:
        result = service.diarize_capture(capture_id)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Capture: {result['capture_id']}")
    print(f"Total audio files: {result['total_audio_files']}")
    print(f"Completed audio files: {result['completed_audio_files']}")
    print(f"Failed audio files: {result['failed_audio_files']}")
    return 0


def run_diarize_status(capture_id: str) -> int:
    service = _get_diarization_service()
    status = service.get_status(capture_id)
    print(f"Capture: {status['capture_id']}")
    print(f"Status: {status['status']}")
    print(f"Total segments: {status['total_segments']}")
    print(f"Completed segments: {status['completed_segments']}")
    print(f"Failed segments: {status['failed_segments']}")
    print(f"Pending segments: {status['pending_segments']}")
    return 0


def run_diarize_list(capture_id: str) -> int:
    service = _get_diarization_service()
    segments = service.list_segments(capture_id)
    if not segments:
        print(f"No diarization segments found for capture: {capture_id}")
        return 0

    for segment in segments:
        print(
            f"[{segment['diarization_status']}] "
            f"{segment['speaker_label']} "
            f"{segment['start_offset_seconds']}-{segment['end_offset_seconds']}s "
            f"{segment['source_audio_path']}"
        )
        if segment["confidence"] is not None:
            print(f"Confidence: {segment['confidence']}")
        if segment["error_message"]:
            print(f"Error: {segment['error_message']}")
    return 0


def _get_summarizer_service() -> SummarizerService:
    state = bootstrap_application(bootstrap_db=True)
    service = state.services["summarizer"]
    assert isinstance(service, SummarizerService)
    return service


def run_summary_generate(capture_id: str, provider_name: str | None = None) -> int:
    service = _get_summarizer_service()
    try:
        result = service.generate_summaries(capture_id, provider_name=provider_name)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Capture: {result['capture_id']}")
    print(f"Summary count: {result['summary_count']}")
    print(f"Provider: {result['provider_name']}")
    if result.get("model_name"):
        print(f"Model: {result['model_name']}")
    return 0


def run_summary_show(capture_id: str) -> int:
    service = _get_summarizer_service()
    summaries = service.list_summaries(capture_id)
    if not summaries:
        print(f"No summaries found for capture: {capture_id}")
        return 0

    for summary in summaries:
        print(f"[{summary['summary_type']}] {summary['title']}")
        print(summary["content"])
        if summary["evidence_snippet"]:
            print(f"Evidence: {summary['evidence_snippet']}")
        if summary["provider_name"]:
            model_suffix = f" ({summary['model_name']})" if summary["model_name"] else ""
            print(f"Provider: {summary['provider_name']}{model_suffix}")
    return 0


def _get_action_extractor_service() -> ActionExtractorService:
    state = bootstrap_application(bootstrap_db=True)
    service = state.services["action_extractor"]
    assert isinstance(service, ActionExtractorService)
    return service


def run_actions_extract(capture_id: str, provider_name: str | None = None) -> int:
    service = _get_action_extractor_service()
    try:
        result = service.extract_capture(capture_id, provider_name=provider_name)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Capture: {result['capture_id']}")
    print(f"Actions: {result['actions']}")
    print(f"Decisions: {result['decisions']}")
    print(f"Follow-ups: {result['follow_ups']}")
    print(f"Provider: {result['provider_name']}")
    if result.get("model_name"):
        print(f"Model: {result['model_name']}")
    return 0


def run_actions_list(capture_id: str) -> int:
    service = _get_action_extractor_service()
    payload = service.list_outputs(capture_id)

    if not payload["actions"] and not payload["decisions"] and not payload["follow_ups"]:
        print(f"No extracted outputs found for capture: {capture_id}")
        return 0

    if payload["actions"]:
        print("Actions:")
        for item in payload["actions"]:
            owner = item["owner_name"] or "Unconfirmed speaker"
            print(f"- {item['description']} [{owner}]")
            if item["evidence_snippet"]:
                print(f"  Evidence: {item['evidence_snippet']}")
            if item["provider_name"]:
                model_suffix = f" ({item['model_name']})" if item["model_name"] else ""
                print(f"  Provider: {item['provider_name']}{model_suffix}")

    if payload["decisions"]:
        print("Decisions:")
        for item in payload["decisions"]:
            print(f"- {item['description']}")
            if item["evidence_snippet"]:
                print(f"  Evidence: {item['evidence_snippet']}")
            if item["provider_name"]:
                model_suffix = f" ({item['model_name']})" if item["model_name"] else ""
                print(f"  Provider: {item['provider_name']}{model_suffix}")

    if payload["follow_ups"]:
        print("Follow-ups:")
        for item in payload["follow_ups"]:
            owner = item["owner_name"] or "Unconfirmed speaker"
            print(f"- [{item['follow_up_type']}] {item['description']} [{owner}]")
            if item["evidence_snippet"]:
                print(f"  Evidence: {item['evidence_snippet']}")
            if item["provider_name"]:
                model_suffix = f" ({item['model_name']})" if item["model_name"] else ""
                print(f"  Provider: {item['provider_name']}{model_suffix}")
    return 0


def run_llm_check() -> int:
    state = bootstrap_application()
    client = build_local_llm_client(state.config)
    try:
        result = client.check()
    except LocalLlmClientError as exc:
        print(str(exc))
        return 1

    print(f"Status: {result['status']}")
    print(f"Base URL: {result['base_url']}")
    print(f"Configured model: {result['model_name']}")
    print(f"Visible models: {len(result['models'])}")
    return 0


def _get_export_service() -> ExportService:
    state = bootstrap_application(bootstrap_db=True)
    service = state.services["export_service"]
    assert isinstance(service, ExportService)
    return service


def _get_session_workflow_service() -> SessionWorkflowService:
    state = bootstrap_application(bootstrap_db=True)
    service = state.services["session_workflow"]
    assert isinstance(service, SessionWorkflowService)
    return service


def run_review_show(capture_id: str, export_format: str) -> int:
    service = _get_export_service()
    if export_format == "json":
        print(service.render_export(capture_id, "json"))
        return 0
    if export_format == "markdown":
        print(service.render_export(capture_id, "markdown"), end="")
        return 0
    print(f"Unsupported review format: {export_format}")
    return 1


def run_review_recent(limit: int) -> int:
    service = _get_export_service()
    payload = service.list_recent_captures(limit=limit)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_review_update_item(
    *,
    item_type: str,
    item_id: int,
    review_status: str,
    description: str | None = None,
    owner_name: str | None = None,
) -> int:
    service = _get_export_service()
    try:
        item = service.review_item(
            item_type=item_type,
            item_id=item_id,
            review_status=review_status,
            reviewed_description=description,
            reviewed_owner_name=owner_name,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(item, ensure_ascii=False))
    return 0


def run_export_capture(capture_id: str, export_format: str) -> int:
    service = _get_session_workflow_service()
    try:
        output_path = service.export_session(capture_id, export_format)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"Exported {export_format}: {output_path}")
    return 0


def run_session_list() -> int:
    service = _get_session_workflow_service()
    print(json.dumps(service.dashboard_payload(), ensure_ascii=False))
    return 0


def run_session_create(title: str | None = None) -> int:
    service = _get_session_workflow_service()
    print(json.dumps(service.create_session(title), ensure_ascii=False))
    return 0


def run_session_get(capture_id: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.get_session(capture_id)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_rename(capture_id: str, title: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.update_session_display_name(capture_id, title)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_record_start(capture_id: str, no_loopback: bool, no_microphone: bool) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.start_session(
            capture_id,
            include_loopback=not no_loopback,
            include_microphone=not no_microphone,
        )
    except (AudioDependencyError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_pause(capture_id: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.pause_session(capture_id)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_resume(capture_id: str, no_loopback: bool, no_microphone: bool) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.resume_session(
            capture_id,
            include_loopback=not no_loopback,
            include_microphone=not no_microphone,
        )
    except (AudioDependencyError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_record_stop(capture_id: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.stop_session(capture_id)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_keep_audio(capture_id: str, enabled: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.update_keep_source_audio(capture_id, enabled == "true")
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_delete_audio(capture_id: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.delete_source_audio(capture_id)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_archive(capture_id: str) -> int:
    service = _get_session_workflow_service()
    try:
        payload = service.archive_session(capture_id)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def run_session_retention_show() -> int:
    service = _get_session_workflow_service()
    print(json.dumps(service.dashboard_payload()["settings"], ensure_ascii=False))
    return 0


def run_session_retention_update(raw_audio_retention_days: int, delete_temp_processing_files: str) -> int:
    service = _get_session_workflow_service()
    print(
        json.dumps(
            service.update_retention_settings(
                raw_audio_retention_days=raw_audio_retention_days,
                delete_temp_processing_files=delete_temp_processing_files == "true",
            ),
            ensure_ascii=False,
        )
    )
    return 0


def run_session_cleanup() -> int:
    service = _get_session_workflow_service()
    print(json.dumps(service.cleanup_retention(), ensure_ascii=False))
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
    if args.command == "session" and args.session_command == "list":
        return run_session_list()
    if args.command == "session" and args.session_command == "create":
        return run_session_create(args.title)
    if args.command == "session" and args.session_command == "get":
        return run_session_get(args.capture_id)
    if args.command == "session" and args.session_command == "rename":
        return run_session_rename(args.capture_id, args.title)
    if args.command == "session" and args.session_command == "record-start":
        return run_session_record_start(args.capture_id, args.no_loopback, args.no_microphone)
    if args.command == "session" and args.session_command == "pause":
        return run_session_pause(args.capture_id)
    if args.command == "session" and args.session_command == "resume":
        return run_session_resume(args.capture_id, args.no_loopback, args.no_microphone)
    if args.command == "session" and args.session_command == "record-stop":
        return run_session_record_stop(args.capture_id)
    if args.command == "session" and args.session_command == "keep-audio":
        return run_session_keep_audio(args.capture_id, args.enabled)
    if args.command == "session" and args.session_command == "delete-audio":
        return run_session_delete_audio(args.capture_id)
    if args.command == "session" and args.session_command == "archive":
        return run_session_archive(args.capture_id)
    if args.command == "session" and args.session_command == "retention-show":
        return run_session_retention_show()
    if args.command == "session" and args.session_command == "retention-update":
        return run_session_retention_update(
            args.raw_audio_retention_days,
            args.delete_temp_processing_files,
        )
    if args.command == "session" and args.session_command == "cleanup":
        return run_session_cleanup()
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
    if args.command == "transcript" and args.transcript_command == "transcribe":
        return run_transcript_transcribe(args.capture_id)
    if args.command == "transcript" and args.transcript_command == "status":
        return run_transcript_status(args.capture_id)
    if args.command == "transcript" and args.transcript_command == "list":
        return run_transcript_list(args.capture_id)
    if args.command == "diarize" and args.diarize_command == "run":
        return run_diarize_run(args.capture_id)
    if args.command == "diarize" and args.diarize_command == "status":
        return run_diarize_status(args.capture_id)
    if args.command == "diarize" and args.diarize_command == "list":
        return run_diarize_list(args.capture_id)
    if args.command == "summary" and args.summary_command == "generate":
        return run_summary_generate(args.capture_id, provider_name=args.provider)
    if args.command == "summary" and args.summary_command == "show":
        return run_summary_show(args.capture_id)
    if args.command == "actions" and args.actions_command == "extract":
        return run_actions_extract(args.capture_id, provider_name=args.provider)
    if args.command == "actions" and args.actions_command == "list":
        return run_actions_list(args.capture_id)
    if args.command == "llm" and args.llm_command == "check":
        return run_llm_check()
    if args.command == "review" and args.review_command == "show":
        return run_review_show(args.capture_id, args.format)
    if args.command == "review" and args.review_command == "recent":
        return run_review_recent(args.limit)
    if args.command == "review" and args.review_command == "update-item":
        return run_review_update_item(
            item_type=args.item_type,
            item_id=args.item_id,
            review_status=args.review_status,
            description=args.description,
            owner_name=args.owner_name,
        )
    if args.command == "export" and args.export_command == "run":
        return run_export_capture(args.capture_id, args.format)

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
