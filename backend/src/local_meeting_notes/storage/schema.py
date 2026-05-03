"""SQLite schema bootstrap for the backend skeleton."""

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS meetings (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        display_name TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'mock',
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transcript_segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        capture_id TEXT NOT NULL DEFAULT '',
        source_chunk_path TEXT NOT NULL DEFAULT '',
        transcription_status TEXT NOT NULL DEFAULT 'pending',
        speaker_label TEXT NOT NULL,
        content TEXT NOT NULL,
        start_offset_seconds INTEGER NOT NULL,
        end_offset_seconds INTEGER NOT NULL,
        provider_name TEXT NOT NULL DEFAULT 'mock',
        model_name TEXT NOT NULL DEFAULT 'mock',
        error_message TEXT,
        is_mock INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        capture_id TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL DEFAULT '',
        content TEXT NOT NULL,
        summary_type TEXT NOT NULL DEFAULT 'mock',
        evidence_snippet TEXT,
        provider_name TEXT NOT NULL DEFAULT 'heuristic',
        model_name TEXT,
        generated_at TEXT,
        review_status TEXT NOT NULL DEFAULT 'generated',
        reviewed_description TEXT,
        reviewed_owner_name TEXT,
        reviewed_at TEXT,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        capture_id TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL,
        owner_name TEXT,
        status TEXT NOT NULL DEFAULT 'open',
        evidence_snippet TEXT,
        start_offset_seconds INTEGER,
        end_offset_seconds INTEGER,
        provider_name TEXT NOT NULL DEFAULT 'heuristic',
        model_name TEXT,
        generated_at TEXT,
        review_status TEXT NOT NULL DEFAULT 'generated',
        reviewed_description TEXT,
        reviewed_owner_name TEXT,
        reviewed_at TEXT,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        capture_id TEXT NOT NULL DEFAULT '',
        evidence_snippet TEXT,
        start_offset_seconds INTEGER,
        end_offset_seconds INTEGER,
        provider_name TEXT NOT NULL DEFAULT 'heuristic',
        model_name TEXT,
        generated_at TEXT,
        review_status TEXT NOT NULL DEFAULT 'generated',
        reviewed_description TEXT,
        reviewed_owner_name TEXT,
        reviewed_at TEXT,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS follow_ups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        capture_id TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL,
        follow_up_type TEXT NOT NULL DEFAULT 'follow_up',
        owner_name TEXT,
        status TEXT NOT NULL DEFAULT 'open',
        evidence_snippet TEXT,
        start_offset_seconds INTEGER,
        end_offset_seconds INTEGER,
        provider_name TEXT NOT NULL DEFAULT 'heuristic',
        model_name TEXT,
        generated_at TEXT,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS diarization_segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        capture_id TEXT NOT NULL DEFAULT '',
        source_audio_path TEXT NOT NULL DEFAULT '',
        diarization_status TEXT NOT NULL DEFAULT 'pending',
        speaker_label TEXT NOT NULL,
        start_offset_seconds INTEGER NOT NULL,
        end_offset_seconds INTEGER NOT NULL,
        provider_name TEXT NOT NULL DEFAULT 'mock',
        confidence REAL,
        error_message TEXT,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
    )
    """,
)
