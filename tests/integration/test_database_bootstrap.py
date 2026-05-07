from local_meeting_notes.bootstrap import bootstrap_application
from local_meeting_notes.config import load_config
from local_meeting_notes.models import MeetingRecord
from local_meeting_notes.session_workflow.service import SessionWorkflowService
from local_meeting_notes.storage.database import bootstrap_database, connection_context
from local_meeting_notes.storage.repository import fetch_table_names, insert_meeting


def test_database_bootstrap_and_basic_persistence(local_tmp_dir) -> None:
    env = {
        "LMN_DATA_DIR": str(local_tmp_dir / "data"),
        "AUDIO_OUTPUT_DIR": str(local_tmp_dir / "data" / "audio"),
        "DATABASE_PATH": str(local_tmp_dir / "data" / "local_meeting_notes.db"),
        "TRANSCRIPT_OUTPUT_DIR": str(local_tmp_dir / "data" / "transcripts"),
        "EXPORT_OUTPUT_DIR": str(local_tmp_dir / "data" / "exports"),
        "TEMP_OUTPUT_DIR": str(local_tmp_dir / "data" / "tmp"),
        "LOG_DIR": str(local_tmp_dir / "data" / "logs"),
        "SESSION_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "session.json"),
        "AUDIO_CAPTURE_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "audio_capture_state.json"),
    }

    state = bootstrap_application(env=env, bootstrap_db=True)

    with connection_context(state.config.database_path) as connection:
        tables = fetch_table_names(connection)
        meeting_id = insert_meeting(
            connection,
            MeetingRecord(
                id=None,
                external_id="mock-test-001",
                title="Mock Test Meeting",
                status="active",
                started_at="2026-04-22T12:00:00+00:00",
            ),
        )
        connection.commit()
        row = connection.execute(
            "SELECT external_id, title FROM meetings WHERE id = ?", (meeting_id,)
        ).fetchone()
        meeting_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(meetings)").fetchall()
        }
        columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(transcript_segments)").fetchall()
        }
        diarization_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(diarization_segments)").fetchall()
        }
        summary_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(summaries)").fetchall()
        }
        action_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(actions)").fetchall()
        }
        decision_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(decisions)").fetchall()
        }
        follow_up_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(follow_ups)").fetchall()
        }
        app_settings_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(app_settings)").fetchall()
        }

    assert {"meetings", "participants", "transcript_segments", "summaries", "actions", "decisions", "follow_ups"}.issubset(tables)
    assert {"capture_id", "created_at", "updated_at", "recorded_seconds", "keep_source_audio", "raw_audio_expires_at", "has_reviewed_items"}.issubset(meeting_columns)
    assert {"capture_id", "source_chunk_path", "transcription_status", "provider_name", "model_name", "error_message"}.issubset(columns)
    assert {"capture_id", "source_audio_path", "diarization_status", "speaker_label", "provider_name", "confidence", "error_message"}.issubset(diarization_columns)
    assert {"capture_id", "title", "evidence_snippet", "provider_name", "model_name", "generated_at"}.issubset(summary_columns)
    review_columns = {"review_status", "reviewed_description", "reviewed_owner_name", "reviewed_at"}
    assert {"capture_id", "evidence_snippet", "start_offset_seconds", "end_offset_seconds", "provider_name", "model_name", "generated_at", *review_columns}.issubset(action_columns)
    assert {"capture_id", "evidence_snippet", "start_offset_seconds", "end_offset_seconds", "provider_name", "model_name", "generated_at", *review_columns}.issubset(decision_columns)
    assert {"capture_id", "follow_up_type", "owner_name", "status", "evidence_snippet", "provider_name", "model_name", "generated_at", *review_columns}.issubset(follow_up_columns)
    assert {"key", "value", "updated_at"}.issubset(app_settings_columns)
    assert row["external_id"] == "mock-test-001"
    assert row["title"] == "Mock Test Meeting"


def test_database_bootstrap_migrates_legacy_meetings_source_fields(local_tmp_dir) -> None:
    config = load_config(
        env={
            "LMN_DATA_DIR": str(local_tmp_dir / "data"),
            "AUDIO_OUTPUT_DIR": str(local_tmp_dir / "data" / "audio"),
            "DATABASE_PATH": str(local_tmp_dir / "data" / "local_meeting_notes.db"),
            "TRANSCRIPT_OUTPUT_DIR": str(local_tmp_dir / "data" / "transcripts"),
            "EXPORT_OUTPUT_DIR": str(local_tmp_dir / "data" / "exports"),
            "TEMP_OUTPUT_DIR": str(local_tmp_dir / "data" / "tmp"),
            "LOG_DIR": str(local_tmp_dir / "data" / "logs"),
            "SESSION_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "session.json"),
            "AUDIO_CAPTURE_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "audio_capture_state.json"),
        }
    )
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connection_context(config.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                session_type TEXT NOT NULL DEFAULT 'ad_hoc',
                planned_start_at TEXT,
                planning_notes TEXT,
                ended_at TEXT,
                capture_id TEXT NOT NULL DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                manual_title INTEGER NOT NULL DEFAULT 1,
                recorded_seconds INTEGER NOT NULL DEFAULT 0,
                last_recording_started_at TEXT,
                reviewed_at TEXT,
                exported_at TEXT,
                archived_at TEXT,
                last_processed_at TEXT,
                last_error TEXT,
                keep_source_audio INTEGER NOT NULL DEFAULT 1,
                source_audio_deleted_at TEXT,
                raw_audio_expires_at TEXT,
                latest_provider_name TEXT,
                latest_model_name TEXT,
                has_reviewed_items INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            INSERT INTO meetings (
                external_id, title, status, started_at, session_type,
                planned_start_at, capture_id, created_at, updated_at
            )
            VALUES (
                'capture:legacy-planned', 'Legacy Planned', 'draft',
                '2026-05-01T00:00:00+00:00', 'planned',
                '2026-05-02T00:00:00+00:00', 'legacy-planned',
                '2026-05-01T00:00:00+00:00', '2026-05-01T00:00:00+00:00'
            )
            """
        )
        connection.commit()

    bootstrap_database(config)

    with connection_context(config.database_path) as connection:
        meeting_columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(meetings)").fetchall()
        }
        legacy_row = connection.execute(
            "SELECT source_type FROM meetings WHERE capture_id = 'legacy-planned'"
        ).fetchone()

    assert {
        "source_type",
        "external_meeting_id",
        "imported_title",
        "imported_metadata_json",
    }.issubset(meeting_columns)
    assert legacy_row["source_type"] == "planned"


def test_legacy_meetings_schema_accepts_new_sessions_after_migration(local_tmp_dir) -> None:
    config = load_config(
        env={
            "LMN_DATA_DIR": str(local_tmp_dir / "data"),
            "AUDIO_OUTPUT_DIR": str(local_tmp_dir / "data" / "audio"),
            "DATABASE_PATH": str(local_tmp_dir / "data" / "local_meeting_notes.db"),
            "TRANSCRIPT_OUTPUT_DIR": str(local_tmp_dir / "data" / "transcripts"),
            "EXPORT_OUTPUT_DIR": str(local_tmp_dir / "data" / "exports"),
            "TEMP_OUTPUT_DIR": str(local_tmp_dir / "data" / "tmp"),
            "LOG_DIR": str(local_tmp_dir / "data" / "logs"),
            "SESSION_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "session.json"),
            "AUDIO_CAPTURE_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "audio_capture_state.json"),
        }
    )
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connection_context(config.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
            """
        )
        connection.commit()

    bootstrap_database(config)
    state = bootstrap_application(env={
        "LMN_DATA_DIR": str(local_tmp_dir / "data"),
        "AUDIO_OUTPUT_DIR": str(local_tmp_dir / "data" / "audio"),
        "DATABASE_PATH": str(local_tmp_dir / "data" / "local_meeting_notes.db"),
        "TRANSCRIPT_OUTPUT_DIR": str(local_tmp_dir / "data" / "transcripts"),
        "EXPORT_OUTPUT_DIR": str(local_tmp_dir / "data" / "exports"),
        "TEMP_OUTPUT_DIR": str(local_tmp_dir / "data" / "tmp"),
        "LOG_DIR": str(local_tmp_dir / "data" / "logs"),
        "SESSION_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "session.json"),
        "AUDIO_CAPTURE_STATE_PATH": str(local_tmp_dir / "data" / "tmp" / "audio_capture_state.json"),
    })
    service = state.services["session_workflow"]
    assert isinstance(service, SessionWorkflowService)

    ad_hoc = service.create_session("Legacy DB Ad Hoc")
    planned = service.create_planned_session(display_name="Legacy DB Planned")

    assert ad_hoc["source_type"] == "ad_hoc"
    assert planned["source_type"] == "planned"
