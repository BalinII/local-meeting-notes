from pathlib import Path

from local_meeting_notes.bootstrap import bootstrap_application
from local_meeting_notes.storage.database import connection_context
from local_meeting_notes.storage.repository import fetch_table_names


def test_bootstrap_registers_services_and_can_bootstrap_db(tmp_path: Path) -> None:
    env = {
        "LMN_DATA_DIR": str(tmp_path / "data"),
        "DATABASE_PATH": str(tmp_path / "data" / "local_meeting_notes.db"),
        "TRANSCRIPT_OUTPUT_DIR": str(tmp_path / "data" / "transcripts"),
        "EXPORT_OUTPUT_DIR": str(tmp_path / "data" / "exports"),
        "TEMP_OUTPUT_DIR": str(tmp_path / "data" / "tmp"),
        "LOG_DIR": str(tmp_path / "data" / "logs"),
        "SESSION_STATE_PATH": str(tmp_path / "data" / "tmp" / "session.json"),
    }

    app_state = bootstrap_application(env=env, bootstrap_db=True)

    assert "storage" in app_state.services
    assert app_state.config.database_path.exists()

    with connection_context(app_state.config.database_path) as connection:
        tables = fetch_table_names(connection)

    assert {"meetings", "participants", "transcript_segments"}.issubset(tables)
