"""Repository helpers for persisted local sessions and outputs."""

from __future__ import annotations

import json
import sqlite3

from ..models import (
    ActionRecord,
    DiarizationSegmentRecord,
    DecisionRecord,
    FollowUpRecord,
    MeetingRecord,
    ParticipantRecord,
    SummaryRecord,
    TranscriptSegmentRecord,
)


def insert_meeting(connection: sqlite3.Connection, meeting: MeetingRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO meetings (
            external_id,
            title,
            status,
            started_at,
            session_type,
            source_type,
            planned_start_at,
            planning_notes,
            external_meeting_id,
            imported_title,
            imported_metadata_json,
            capture_id,
            ended_at,
            created_at,
            updated_at,
            manual_title,
            recorded_seconds,
            last_recording_started_at,
            reviewed_at,
            exported_at,
            archived_at,
            last_processed_at,
            last_error,
            keep_source_audio,
            source_audio_deleted_at,
            raw_audio_expires_at,
            latest_provider_name,
            latest_model_name,
            has_reviewed_items
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            meeting.external_id,
            meeting.title,
            meeting.status,
            meeting.started_at,
            meeting.session_type,
            meeting.source_type,
            meeting.planned_start_at,
            meeting.planning_notes,
            meeting.external_meeting_id,
            meeting.imported_title,
            meeting.imported_metadata_json,
            meeting.capture_id,
            meeting.ended_at,
            meeting.created_at,
            meeting.updated_at,
            int(meeting.manual_title),
            meeting.recorded_seconds,
            meeting.last_recording_started_at,
            meeting.reviewed_at,
            meeting.exported_at,
            meeting.archived_at,
            meeting.last_processed_at,
            meeting.last_error,
            int(meeting.keep_source_audio),
            meeting.source_audio_deleted_at,
            meeting.raw_audio_expires_at,
            meeting.latest_provider_name,
            meeting.latest_model_name,
            int(meeting.has_reviewed_items),
        ),
    )
    return int(cursor.lastrowid)


def insert_participant(connection: sqlite3.Connection, participant: ParticipantRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO participants (meeting_id, display_name, source)
        VALUES (?, ?, ?)
        """,
        (participant.meeting_id, participant.display_name, participant.source),
    )
    return int(cursor.lastrowid)


def insert_transcript_segment(
    connection: sqlite3.Connection, segment: TranscriptSegmentRecord
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO transcript_segments (
            meeting_id,
            capture_id,
            source_chunk_path,
            transcription_status,
            speaker_label,
            content,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            error_message,
            is_mock
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            segment.meeting_id,
            segment.capture_id,
            segment.source_chunk_path,
            segment.transcription_status,
            segment.speaker_label,
            segment.content,
            segment.start_offset_seconds,
            segment.end_offset_seconds,
            segment.provider_name,
            segment.model_name,
            segment.error_message,
            int(segment.is_mock),
        ),
    )
    return int(cursor.lastrowid)


def insert_summary(connection: sqlite3.Connection, summary: SummaryRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO summaries (
            meeting_id,
            capture_id,
            title,
            content,
            summary_type,
            evidence_snippet,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            summary.meeting_id,
            summary.capture_id,
            summary.title,
            summary.content,
            summary.summary_type,
            summary.evidence_snippet,
            summary.provider_name,
            summary.model_name,
            summary.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_action(connection: sqlite3.Connection, action: ActionRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO actions (
            meeting_id,
            capture_id,
            description,
            owner_name,
            status,
            evidence_snippet,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action.meeting_id,
            action.capture_id,
            action.description,
            action.owner_name,
            action.status,
            action.evidence_snippet,
            action.start_offset_seconds,
            action.end_offset_seconds,
            action.provider_name,
            action.model_name,
            action.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_decision(connection: sqlite3.Connection, decision: DecisionRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO decisions (
            meeting_id,
            description,
            capture_id,
            evidence_snippet,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision.meeting_id,
            decision.description,
            decision.capture_id,
            decision.evidence_snippet,
            decision.start_offset_seconds,
            decision.end_offset_seconds,
            decision.provider_name,
            decision.model_name,
            decision.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_follow_up(connection: sqlite3.Connection, follow_up: FollowUpRecord) -> int:
    cursor = connection.execute(
        """
        INSERT INTO follow_ups (
            meeting_id,
            capture_id,
            description,
            follow_up_type,
            owner_name,
            status,
            evidence_snippet,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            model_name,
            generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            follow_up.meeting_id,
            follow_up.capture_id,
            follow_up.description,
            follow_up.follow_up_type,
            follow_up.owner_name,
            follow_up.status,
            follow_up.evidence_snippet,
            follow_up.start_offset_seconds,
            follow_up.end_offset_seconds,
            follow_up.provider_name,
            follow_up.model_name,
            follow_up.generated_at,
        ),
    )
    return int(cursor.lastrowid)


def update_meeting_status(
    connection: sqlite3.Connection, external_id: str, status: str, ended_at: str | None = None
) -> None:
    connection.execute(
        "UPDATE meetings SET status = ?, ended_at = ? WHERE external_id = ?",
        (status, ended_at, external_id),
    )


def fetch_meeting_by_capture_id(connection: sqlite3.Connection, capture_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM meetings
        WHERE capture_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (capture_id,),
    ).fetchone()


def fetch_recent_meetings(connection: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM meetings
        WHERE capture_id <> ''
        ORDER BY COALESCE(updated_at, created_at, started_at) DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def fetch_cross_session_action_items(connection: sqlite3.Connection, limit: int = 100) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM (
            SELECT
                actions.id AS id,
                'action' AS item_type,
                actions.capture_id AS capture_id,
                meetings.title AS source_display_name,
                meetings.status AS source_lifecycle_state,
                meetings.updated_at AS source_updated_at,
                actions.description AS description,
                actions.owner_name AS owner_name,
                actions.status AS workflow_state,
                actions.evidence_snippet AS evidence_snippet,
                actions.start_offset_seconds AS start_offset_seconds,
                actions.end_offset_seconds AS end_offset_seconds,
                actions.provider_name AS provider_name,
                actions.model_name AS model_name,
                actions.generated_at AS generated_at,
                actions.review_status AS review_status,
                actions.reviewed_description AS reviewed_description,
                actions.reviewed_owner_name AS reviewed_owner_name,
                actions.reviewed_at AS reviewed_at,
                actions.due_at AS due_at,
                actions.notes AS notes,
                actions.carry_source_capture_id AS carry_source_capture_id,
                actions.carry_count AS carry_count
            FROM actions
            INNER JOIN meetings ON meetings.id = actions.meeting_id
            WHERE actions.review_status <> 'rejected'

            UNION ALL

            SELECT
                decisions.id AS id,
                'decision' AS item_type,
                decisions.capture_id AS capture_id,
                meetings.title AS source_display_name,
                meetings.status AS source_lifecycle_state,
                meetings.updated_at AS source_updated_at,
                decisions.description AS description,
                NULL AS owner_name,
                'open' AS workflow_state,
                decisions.evidence_snippet AS evidence_snippet,
                decisions.start_offset_seconds AS start_offset_seconds,
                decisions.end_offset_seconds AS end_offset_seconds,
                decisions.provider_name AS provider_name,
                decisions.model_name AS model_name,
                decisions.generated_at AS generated_at,
                decisions.review_status AS review_status,
                decisions.reviewed_description AS reviewed_description,
                decisions.reviewed_owner_name AS reviewed_owner_name,
                decisions.reviewed_at AS reviewed_at,
                NULL AS due_at,
                NULL AS notes,
                NULL AS carry_source_capture_id,
                0 AS carry_count
            FROM decisions
            INNER JOIN meetings ON meetings.id = decisions.meeting_id
            WHERE decisions.review_status <> 'rejected'

            UNION ALL

            SELECT
                follow_ups.id AS id,
                follow_ups.follow_up_type AS item_type,
                follow_ups.capture_id AS capture_id,
                meetings.title AS source_display_name,
                meetings.status AS source_lifecycle_state,
                meetings.updated_at AS source_updated_at,
                follow_ups.description AS description,
                follow_ups.owner_name AS owner_name,
                follow_ups.status AS workflow_state,
                follow_ups.evidence_snippet AS evidence_snippet,
                follow_ups.start_offset_seconds AS start_offset_seconds,
                follow_ups.end_offset_seconds AS end_offset_seconds,
                follow_ups.provider_name AS provider_name,
                follow_ups.model_name AS model_name,
                follow_ups.generated_at AS generated_at,
                follow_ups.review_status AS review_status,
                follow_ups.reviewed_description AS reviewed_description,
                follow_ups.reviewed_owner_name AS reviewed_owner_name,
                follow_ups.reviewed_at AS reviewed_at,
                follow_ups.due_at AS due_at,
                follow_ups.notes AS notes,
                follow_ups.carry_source_capture_id AS carry_source_capture_id,
                follow_ups.carry_count AS carry_count
            FROM follow_ups
            INNER JOIN meetings ON meetings.id = follow_ups.meeting_id
            WHERE follow_ups.review_status <> 'rejected'
        )
        ORDER BY COALESCE(reviewed_at, generated_at, source_updated_at) DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def fetch_session_library_rows(connection: sqlite3.Connection, limit: int = 500) -> list[sqlite3.Row]:
    safe_limit = max(1, min(int(limit), 1000))
    return connection.execute(
        """
        SELECT
            meetings.*,
            GROUP_CONCAT(DISTINCT summaries.provider_name) AS summary_providers,
            GROUP_CONCAT(DISTINCT summaries.model_name) AS summary_models,
            GROUP_CONCAT(DISTINCT actions.provider_name) AS action_providers,
            GROUP_CONCAT(DISTINCT actions.model_name) AS action_models,
            GROUP_CONCAT(DISTINCT decisions.provider_name) AS decision_providers,
            GROUP_CONCAT(DISTINCT decisions.model_name) AS decision_models,
            GROUP_CONCAT(DISTINCT follow_ups.provider_name) AS follow_up_providers,
            GROUP_CONCAT(DISTINCT follow_ups.model_name) AS follow_up_models
        FROM meetings
        LEFT JOIN summaries ON summaries.capture_id = meetings.capture_id
        LEFT JOIN actions ON actions.capture_id = meetings.capture_id
        LEFT JOIN decisions ON decisions.capture_id = meetings.capture_id
        LEFT JOIN follow_ups ON follow_ups.capture_id = meetings.capture_id
        WHERE meetings.capture_id <> ''
        GROUP BY meetings.id
        ORDER BY COALESCE(meetings.updated_at, meetings.created_at, meetings.started_at) DESC, meetings.id DESC
        LIMIT ?
        """,
        (safe_limit,),
    ).fetchall()


def search_capture_content(
    connection: sqlite3.Connection,
    query: str,
    scopes: list[str] | None = None,
    limit: int = 120,
) -> list[sqlite3.Row]:
    cleaned_query = query.strip().lower()
    if not cleaned_query:
        return []
    like_query = f"%{cleaned_query}%"
    safe_limit = max(1, min(int(limit), 500))
    allowed_scopes = {
        "session",
        "summary",
        "action",
        "decision",
        "follow_up",
        "blocker_risk",
        "open_question",
        "transcript",
    }
    selected_scopes = [scope for scope in (scopes or []) if scope in allowed_scopes]
    scope_filter = ""
    parameters: list[object] = [like_query]
    if selected_scopes:
        placeholders = ", ".join("?" for _ in selected_scopes)
        scope_filter = f" AND item_type IN ({placeholders})"
        parameters.extend(selected_scopes)
    parameters.append(safe_limit)
    return connection.execute(
        """
        WITH searchable AS (
            SELECT
                meetings.capture_id AS capture_id,
                meetings.title AS session_display_name,
                meetings.status AS lifecycle_state,
                'session' AS item_type,
                'display_name' AS field_name,
                meetings.title AS content,
                meetings.updated_at AS item_updated_at,
                10 AS rank_weight
            FROM meetings
            WHERE meetings.capture_id <> ''

            UNION ALL

            SELECT
                meetings.capture_id,
                meetings.title,
                meetings.status,
                'session' AS item_type,
                'capture_id' AS field_name,
                meetings.capture_id AS content,
                meetings.updated_at AS item_updated_at,
                20 AS rank_weight
            FROM meetings
            WHERE meetings.capture_id <> ''

            UNION ALL

            SELECT
                transcript_segments.capture_id,
                meetings.title,
                meetings.status,
                'transcript' AS item_type,
                COALESCE(transcript_segments.speaker_label, 'transcript') AS field_name,
                transcript_segments.content AS content,
                meetings.updated_at AS item_updated_at,
                90 AS rank_weight
            FROM transcript_segments
            INNER JOIN meetings ON meetings.capture_id = transcript_segments.capture_id
            WHERE transcript_segments.content IS NOT NULL

            UNION ALL

            SELECT
                summaries.capture_id,
                meetings.title,
                meetings.status,
                'summary' AS item_type,
                summaries.summary_type AS field_name,
                summaries.content AS content,
                COALESCE(summaries.reviewed_at, summaries.generated_at, meetings.updated_at) AS item_updated_at,
                30 AS rank_weight
            FROM summaries
            INNER JOIN meetings ON meetings.capture_id = summaries.capture_id

            UNION ALL

            SELECT
                summaries.capture_id,
                meetings.title,
                meetings.status,
                'summary' AS item_type,
                summaries.summary_type || '_evidence' AS field_name,
                summaries.evidence_snippet AS content,
                COALESCE(summaries.reviewed_at, summaries.generated_at, meetings.updated_at) AS item_updated_at,
                55 AS rank_weight
            FROM summaries
            INNER JOIN meetings ON meetings.capture_id = summaries.capture_id
            WHERE summaries.evidence_snippet IS NOT NULL

            UNION ALL

            SELECT
                actions.capture_id,
                meetings.title,
                meetings.status,
                'action' AS item_type,
                'actions' AS field_name,
                COALESCE(actions.reviewed_description, actions.description) AS content,
                COALESCE(actions.reviewed_at, actions.generated_at, meetings.updated_at) AS item_updated_at,
                CASE WHEN actions.reviewed_at IS NOT NULL OR actions.review_status IN ('accepted', 'edited') THEN 25 ELSE 40 END AS rank_weight
            FROM actions
            INNER JOIN meetings ON meetings.capture_id = actions.capture_id
            WHERE actions.review_status <> 'rejected'

            UNION ALL

            SELECT
                actions.capture_id,
                meetings.title,
                meetings.status,
                'action' AS item_type,
                'action_evidence' AS field_name,
                actions.evidence_snippet AS content,
                COALESCE(actions.reviewed_at, actions.generated_at, meetings.updated_at) AS item_updated_at,
                65 AS rank_weight
            FROM actions
            INNER JOIN meetings ON meetings.capture_id = actions.capture_id
            WHERE actions.evidence_snippet IS NOT NULL
                AND actions.review_status <> 'rejected'

            UNION ALL

            SELECT
                decisions.capture_id,
                meetings.title,
                meetings.status,
                'decision' AS item_type,
                'decisions' AS field_name,
                COALESCE(decisions.reviewed_description, decisions.description) AS content,
                COALESCE(decisions.reviewed_at, decisions.generated_at, meetings.updated_at) AS item_updated_at,
                CASE WHEN decisions.reviewed_at IS NOT NULL OR decisions.review_status IN ('accepted', 'edited') THEN 22 ELSE 38 END AS rank_weight
            FROM decisions
            INNER JOIN meetings ON meetings.capture_id = decisions.capture_id
            WHERE decisions.review_status <> 'rejected'

            UNION ALL

            SELECT
                decisions.capture_id,
                meetings.title,
                meetings.status,
                'decision' AS item_type,
                'decision_evidence' AS field_name,
                decisions.evidence_snippet AS content,
                COALESCE(decisions.reviewed_at, decisions.generated_at, meetings.updated_at) AS item_updated_at,
                63 AS rank_weight
            FROM decisions
            INNER JOIN meetings ON meetings.capture_id = decisions.capture_id
            WHERE decisions.evidence_snippet IS NOT NULL
                AND decisions.review_status <> 'rejected'

            UNION ALL

            SELECT
                follow_ups.capture_id,
                meetings.title,
                meetings.status,
                follow_ups.follow_up_type AS item_type,
                follow_ups.follow_up_type AS field_name,
                COALESCE(follow_ups.reviewed_description, follow_ups.description) AS content,
                COALESCE(follow_ups.reviewed_at, follow_ups.generated_at, meetings.updated_at) AS item_updated_at,
                CASE WHEN follow_ups.reviewed_at IS NOT NULL OR follow_ups.review_status IN ('accepted', 'edited') THEN 28 ELSE 42 END AS rank_weight
            FROM follow_ups
            INNER JOIN meetings ON meetings.capture_id = follow_ups.capture_id
            WHERE follow_ups.review_status <> 'rejected'

            UNION ALL

            SELECT
                follow_ups.capture_id,
                meetings.title,
                meetings.status,
                follow_ups.follow_up_type AS item_type,
                follow_ups.follow_up_type || '_evidence' AS field_name,
                follow_ups.evidence_snippet AS content,
                COALESCE(follow_ups.reviewed_at, follow_ups.generated_at, meetings.updated_at) AS item_updated_at,
                68 AS rank_weight
            FROM follow_ups
            INNER JOIN meetings ON meetings.capture_id = follow_ups.capture_id
            WHERE follow_ups.evidence_snippet IS NOT NULL
                AND follow_ups.review_status <> 'rejected'
        )
        SELECT
            capture_id,
            session_display_name,
            lifecycle_state,
            item_type,
            field_name,
            content,
            item_updated_at,
            rank_weight,
            REPLACE(LOWER(COALESCE(content, '')), CHAR(10), ' ') AS lowered_content
        FROM searchable
        WHERE REPLACE(LOWER(COALESCE(content, '')), CHAR(10), ' ') LIKE ?
        """ + scope_filter + """
        ORDER BY rank_weight ASC, item_updated_at DESC, capture_id DESC
        LIMIT ?
        """,
        parameters,
    ).fetchall()


def update_workspace_item_status(
    connection: sqlite3.Connection,
    *,
    item_type: str,
    item_id: int,
    workflow_status: str,
    reviewed_at: str,
) -> sqlite3.Row | None:
    table_name = _table_name_for_extracted_item(item_type)
    if workflow_status == "carried_forward":
        connection.execute(
            f"""
            UPDATE {table_name}
            SET status = ?, reviewed_at = ?, carry_count = COALESCE(carry_count, 0) + 1,
                carry_source_capture_id = COALESCE(carry_source_capture_id, capture_id)
            WHERE id = ?
            """,
            (workflow_status, reviewed_at, item_id),
        )
    else:
        connection.execute(
            f"UPDATE {table_name} SET status = ?, reviewed_at = ? WHERE id = ?",
            (workflow_status, reviewed_at, item_id),
        )
    if item_type == "action":
        return connection.execute(
            """
            SELECT
                actions.id AS id,
                'action' AS item_type,
                actions.capture_id AS capture_id,
                meetings.title AS source_display_name,
                meetings.status AS source_lifecycle_state,
                meetings.updated_at AS source_updated_at,
                actions.description AS description,
                actions.owner_name AS owner_name,
                actions.status AS workflow_state,
                actions.evidence_snippet AS evidence_snippet,
                actions.start_offset_seconds AS start_offset_seconds,
                actions.end_offset_seconds AS end_offset_seconds,
                actions.provider_name AS provider_name,
                actions.model_name AS model_name,
                actions.generated_at AS generated_at,
                actions.review_status AS review_status,
                actions.reviewed_description AS reviewed_description,
                actions.reviewed_owner_name AS reviewed_owner_name,
                actions.reviewed_at AS reviewed_at,
                actions.due_at AS due_at,
                actions.notes AS notes,
                actions.carry_source_capture_id AS carry_source_capture_id,
                actions.carry_count AS carry_count
            FROM actions
            INNER JOIN meetings ON meetings.id = actions.meeting_id
            WHERE actions.id = ?
            """,
            (item_id,),
        ).fetchone()
    if item_type == "follow_up":
        return connection.execute(
            """
            SELECT
                follow_ups.id AS id,
                follow_ups.follow_up_type AS item_type,
                follow_ups.capture_id AS capture_id,
                meetings.title AS source_display_name,
                meetings.status AS source_lifecycle_state,
                meetings.updated_at AS source_updated_at,
                follow_ups.description AS description,
                follow_ups.owner_name AS owner_name,
                follow_ups.status AS workflow_state,
                follow_ups.evidence_snippet AS evidence_snippet,
                follow_ups.start_offset_seconds AS start_offset_seconds,
                follow_ups.end_offset_seconds AS end_offset_seconds,
                follow_ups.provider_name AS provider_name,
                follow_ups.model_name AS model_name,
                follow_ups.generated_at AS generated_at,
                follow_ups.review_status AS review_status,
                follow_ups.reviewed_description AS reviewed_description,
                follow_ups.reviewed_owner_name AS reviewed_owner_name,
                follow_ups.reviewed_at AS reviewed_at,
                follow_ups.due_at AS due_at,
                follow_ups.notes AS notes,
                follow_ups.carry_source_capture_id AS carry_source_capture_id,
                follow_ups.carry_count AS carry_count
            FROM follow_ups
            INNER JOIN meetings ON meetings.id = follow_ups.meeting_id
            WHERE follow_ups.id = ?
            """,
            (item_id,),
        ).fetchone()
    return None


def update_workspace_item_details(
    connection: sqlite3.Connection,
    *,
    item_type: str,
    item_id: int,
    due_at: str | None,
    notes: str | None,
    reviewed_at: str,
) -> sqlite3.Row | None:
    table_name = _table_name_for_extracted_item(item_type)
    connection.execute(
        f"UPDATE {table_name} SET due_at = ?, notes = ?, reviewed_at = ? WHERE id = ?",
        (due_at, notes, reviewed_at, item_id),
    )
    return update_workspace_item_status(
        connection,
        item_type=item_type,
        item_id=item_id,
        workflow_status=connection.execute(f"SELECT status FROM {table_name} WHERE id = ?", (item_id,)).fetchone()["status"],
        reviewed_at=reviewed_at,
    )


def update_meeting_fields(
    connection: sqlite3.Connection,
    capture_id: str,
    **fields: object,
) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = [int(value) if isinstance(value, bool) else value for value in fields.values()]
    values.append(capture_id)
    connection.execute(
        f"UPDATE meetings SET {assignments} WHERE capture_id = ?",
        values,
    )


def upsert_app_setting(connection: sqlite3.Connection, key: str, value: object, updated_at: str) -> None:
    connection.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, json.dumps(value), updated_at),
    )


def fetch_app_settings(connection: sqlite3.Connection) -> dict[str, object]:
    rows = connection.execute("SELECT key, value FROM app_settings").fetchall()
    return {str(row["key"]): json.loads(str(row["value"])) for row in rows}


def fetch_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}


def ensure_meeting_for_capture(connection: sqlite3.Connection, capture_id: str) -> int:
    row = fetch_meeting_by_capture_id(connection, capture_id)
    if row is not None:
        return int(row["id"])

    return insert_meeting(
        connection,
        MeetingRecord(
            id=None,
            external_id=f"capture:{capture_id}",
            title=f"Audio Capture {capture_id}",
            status="draft",
            started_at="1970-01-01T00:00:00+00:00",
            capture_id=capture_id,
            created_at="1970-01-01T00:00:00+00:00",
            updated_at="1970-01-01T00:00:00+00:00",
        ),
    )


def delete_transcript_segments_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM transcript_segments WHERE capture_id = ?", (capture_id,))


def fetch_transcript_segments_for_capture(
    connection: sqlite3.Connection, capture_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM transcript_segments
        WHERE capture_id = ?
        ORDER BY start_offset_seconds, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_transcription_status(connection: sqlite3.Connection, capture_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            capture_id,
            COUNT(*) AS total_segments,
            SUM(CASE WHEN transcription_status = 'completed' THEN 1 ELSE 0 END) AS completed_segments,
            SUM(CASE WHEN transcription_status = 'failed' THEN 1 ELSE 0 END) AS failed_segments,
            SUM(CASE WHEN transcription_status = 'pending' THEN 1 ELSE 0 END) AS pending_segments
        FROM transcript_segments
        WHERE capture_id = ?
        GROUP BY capture_id
        """,
        (capture_id,),
    ).fetchone()


def delete_summaries_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM summaries WHERE capture_id = ?", (capture_id,))


def delete_actions_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM actions WHERE capture_id = ?", (capture_id,))


def delete_decisions_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM decisions WHERE capture_id = ?", (capture_id,))


def delete_follow_ups_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM follow_ups WHERE capture_id = ?", (capture_id,))


def fetch_summaries_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM summaries
        WHERE capture_id = ?
        ORDER BY summary_type, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_actions_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM actions
        WHERE capture_id = ?
        ORDER BY id
        """,
        (capture_id,),
    ).fetchall()


def fetch_decisions_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM decisions
        WHERE capture_id = ?
        ORDER BY id
        """,
        (capture_id,),
    ).fetchall()


def fetch_follow_ups_for_capture(connection: sqlite3.Connection, capture_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM follow_ups
        WHERE capture_id = ?
        ORDER BY follow_up_type, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_recent_capture_activity(
    connection: sqlite3.Connection, limit: int = 12
) -> list[sqlite3.Row]:
    safe_limit = max(1, min(int(limit), 100))
    return connection.execute(
        """
        WITH capture_events AS (
            SELECT
                capture_id,
                generated_at,
                provider_name,
                model_name,
                NULL AS reviewed_at,
                'generated' AS review_status
            FROM summaries
            WHERE capture_id <> ''
            UNION ALL
            SELECT
                capture_id,
                generated_at,
                provider_name,
                model_name,
                reviewed_at,
                COALESCE(review_status, 'generated') AS review_status
            FROM actions
            WHERE capture_id <> ''
            UNION ALL
            SELECT
                capture_id,
                generated_at,
                provider_name,
                model_name,
                reviewed_at,
                COALESCE(review_status, 'generated') AS review_status
            FROM decisions
            WHERE capture_id <> ''
            UNION ALL
            SELECT
                capture_id,
                generated_at,
                provider_name,
                model_name,
                reviewed_at,
                COALESCE(review_status, 'generated') AS review_status
            FROM follow_ups
            WHERE capture_id <> ''
        )
        SELECT
            capture_id,
            MIN(generated_at) AS first_generated_at,
            MAX(generated_at) AS latest_generated_at,
            MAX(reviewed_at) AS latest_reviewed_at,
            GROUP_CONCAT(DISTINCT provider_name) AS providers,
            GROUP_CONCAT(DISTINCT model_name) AS models,
            MAX(
                CASE
                    WHEN review_status IN ('accepted', 'edited', 'rejected') OR reviewed_at IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS has_reviewed_items
        FROM capture_events
        GROUP BY capture_id
        ORDER BY COALESCE(MAX(generated_at), MAX(reviewed_at)) DESC, capture_id DESC
        LIMIT ?
        """,
        (safe_limit,),
    ).fetchall()


def update_extracted_item_review(
    connection: sqlite3.Connection,
    *,
    item_type: str,
    item_id: int,
    review_status: str,
    reviewed_description: str | None,
    reviewed_owner_name: str | None,
    reviewed_at: str,
) -> sqlite3.Row | None:
    table_name = _table_name_for_extracted_item(item_type)
    connection.execute(
        f"""
        UPDATE {table_name}
        SET
            review_status = ?,
            reviewed_description = ?,
            reviewed_owner_name = ?,
            reviewed_at = ?
        WHERE id = ?
        """,
        (review_status, reviewed_description, reviewed_owner_name, reviewed_at, item_id),
    )
    return connection.execute(
        f"""
        SELECT *
        FROM {table_name}
        WHERE id = ?
        """,
        (item_id,),
    ).fetchone()


def _table_name_for_extracted_item(item_type: str) -> str:
    if item_type == "action":
        return "actions"
    if item_type == "decision":
        return "decisions"
    if item_type == "follow_up":
        return "follow_ups"
    raise ValueError(f"Unsupported review item type: {item_type}")


def insert_diarization_segment(
    connection: sqlite3.Connection, segment: DiarizationSegmentRecord
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO diarization_segments (
            meeting_id,
            capture_id,
            source_audio_path,
            diarization_status,
            speaker_label,
            start_offset_seconds,
            end_offset_seconds,
            provider_name,
            confidence,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            segment.meeting_id,
            segment.capture_id,
            segment.source_audio_path,
            segment.diarization_status,
            segment.speaker_label,
            segment.start_offset_seconds,
            segment.end_offset_seconds,
            segment.provider_name,
            segment.confidence,
            segment.error_message,
        ),
    )
    return int(cursor.lastrowid)


def delete_diarization_segments_for_capture(connection: sqlite3.Connection, capture_id: str) -> None:
    connection.execute("DELETE FROM diarization_segments WHERE capture_id = ?", (capture_id,))


def fetch_diarization_segments_for_capture(
    connection: sqlite3.Connection, capture_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT *
        FROM diarization_segments
        WHERE capture_id = ?
        ORDER BY start_offset_seconds, id
        """,
        (capture_id,),
    ).fetchall()


def fetch_diarization_status(connection: sqlite3.Connection, capture_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            capture_id,
            COUNT(*) AS total_segments,
            SUM(CASE WHEN diarization_status = 'completed' THEN 1 ELSE 0 END) AS completed_segments,
            SUM(CASE WHEN diarization_status = 'failed' THEN 1 ELSE 0 END) AS failed_segments,
            SUM(CASE WHEN diarization_status = 'pending' THEN 1 ELSE 0 END) AS pending_segments
        FROM diarization_segments
        WHERE capture_id = ?
        GROUP BY capture_id
        """,
        (capture_id,),
    ).fetchone()


def apply_speaker_labels_to_transcript_segments(
    connection: sqlite3.Connection, capture_id: str
) -> None:
    transcript_rows = fetch_transcript_segments_for_capture(connection, capture_id)
    diarization_rows = fetch_diarization_segments_for_capture(connection, capture_id)
    for transcript in transcript_rows:
        best_label = "Unknown"
        best_overlap_ratio = 0.0
        best_midpoint_distance = None
        transcript_duration = max(
            0.5, transcript["end_offset_seconds"] - transcript["start_offset_seconds"]
        )
        transcript_midpoint = (
            transcript["start_offset_seconds"] + transcript["end_offset_seconds"]
        ) / 2
        for diarization in diarization_rows:
            if diarization["diarization_status"] != "completed":
                continue
            overlap = min(
                transcript["end_offset_seconds"], diarization["end_offset_seconds"]
            ) - max(transcript["start_offset_seconds"], diarization["start_offset_seconds"])
            if overlap > 0:
                overlap_ratio = overlap / transcript_duration
                if overlap_ratio > best_overlap_ratio:
                    best_overlap_ratio = overlap_ratio
                    best_label = diarization["speaker_label"]
                    best_midpoint_distance = 0.0
                continue

            diarization_midpoint = (
                diarization["start_offset_seconds"] + diarization["end_offset_seconds"]
            ) / 2
            midpoint_distance = abs(diarization_midpoint - transcript_midpoint)
            if best_overlap_ratio == 0 and (
                best_midpoint_distance is None or midpoint_distance < best_midpoint_distance
            ):
                best_midpoint_distance = midpoint_distance
                best_label = diarization["speaker_label"]

        if best_overlap_ratio < 0.2 and (best_midpoint_distance is None or best_midpoint_distance > 2.0):
            best_label = "Unknown"
        connection.execute(
            "UPDATE transcript_segments SET speaker_label = ? WHERE id = ?",
            (best_label, transcript["id"]),
        )
