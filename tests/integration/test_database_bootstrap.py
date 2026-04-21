from local_meeting_notes.bootstrap import bootstrap_application
from local_meeting_notes.models import MeetingRecord
from local_meeting_notes.storage.database import connection_context
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

    assert {"meetings", "participants", "transcript_segments", "summaries", "actions", "decisions"}.issubset(tables)
    assert row["external_id"] == "mock-test-001"
    assert row["title"] == "Mock Test Meeting"
