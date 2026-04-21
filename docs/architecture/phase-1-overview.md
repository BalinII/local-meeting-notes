# Phase 1 Overview

Phase 1 establishes a clean local-first structure for a Windows desktop app.

## Decisions

- Desktop shell: Tauri with React
- Backend: Python package under `backend/src/local_meeting_notes`
- Persistence target: SQLite and local filesystem
- Platform emphasis: Windows audio capture and Windows development scripts

## Explicit Non-Goals

- No Teams bot
- No production audio capture logic
- No real transcription or diarization implementation
- No cloud-first architecture
