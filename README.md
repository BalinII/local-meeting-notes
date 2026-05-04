# Local Meeting Notes

Local Meeting Notes is a Windows-first, local-first desktop prototype for recording meetings, transcribing audio, generating meeting notes, reviewing extracted outcomes, and exporting shareable artifacts without joining meetings as a bot.

It is an internal prototype, not a production SaaS app. Accuracy, traceability, and honest uncertainty matter more than polish.

## Current Product Shape

The current app supports a local recording-to-review workflow:

1. create a new recording session and optionally name the meeting
2. record microphone audio locally
3. pause, resume, stop, and process the session
4. review summaries, actions, decisions, follow-ups, blockers/risks, and open questions
5. accept, edit, or reject extracted items
6. export Markdown, HTML, or JSON
7. browse recent sessions, search across local content, and use global action/memory views
8. create lightweight planned sessions and start recording from a planned session
9. optionally create a session from lightweight upcoming-meeting context (mock/local staged path)

The safest demo mode is microphone-only recording. System audio / loopback capture is constrained and hardware-dependent; parallel mic plus loopback processing is not treated as a reliable aligned transcript yet.

## What It Does

- Runs locally on Windows through a Tauri desktop shell.
- Stores data locally in SQLite and the filesystem.
- Captures audio into local chunks.
- Transcribes captured audio locally.
- Applies generic speaker labels with best-effort diarization.
- Generates executive and detailed summaries.
- Extracts actions, decisions, follow-ups, blockers/risks, and open questions.
- Preserves evidence snippets and provider/model metadata where available.
- Supports human review before export.
- Keeps reviewed text separate from generated text.
- Falls back to heuristic summary/extraction when local LLM output is unavailable, invalid, weak, or timed out.

## What It Does Not Do

- It does not join meetings as a visible bot.
- It does not implement Microsoft auth.
- It does not implement Outlook or Teams production integration.
- It does not identify real participants beyond generic or transcript-derived labels.
- It does not provide cloud sync, multi-user collaboration, enterprise auth, or production observability.

## Repository Map

```text
app/                         Tauri + React desktop shell
backend/src/local_meeting_notes/
  audio_capture/             local Windows audio capture
  transcription_engine/      batch transcription
  diarization_engine/        generic speaker-turn labeling
  summarizer/                summary generation
  action_extractor/          actions/decisions/follow-ups extraction
  export_service/            markdown/html/json export
  storage/                   SQLite schema and repository helpers
  local_llm/                 Ollama-first local LLM client boundary
docs/
  current-status.md
  troubleshooting.md
  demo/demo-walkthrough.md
  roadmap.md
```

## Prerequisites

- Windows 11 preferred
- Python 3.12+
- Node.js 20+
- Rust stable with MSVC toolchain
- WebView2 runtime for Tauri
- Optional: Ollama for the `local_llm` provider

## Quick Start

From repo root:

```powershell
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
python -m pip install --upgrade pip
pip install -e .\backend
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
```

Install and run the desktop shell:

```powershell
cd .\app
npm install
npm run tauri:dev
```

In the app:

1. Enter a meeting/call name if useful.
2. Use `New Recording` for ad hoc capture (default), or create a lightweight planned session and start from that session.
3. Use `Pause`, `Resume`, and `Stop and Process`.
4. Review generated notes.
5. Export Markdown, HTML, or JSON.

## Backend CLI Essentials

Use these from repo root with the virtual environment active.

```powershell
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app session create --title "Demo Meeting"
python -m local_meeting_notes.app session record-start --capture-id "<capture-id>" --no-loopback
python -m local_meeting_notes.app session pause --capture-id "<capture-id>"
python -m local_meeting_notes.app session resume --capture-id "<capture-id>" --no-loopback
python -m local_meeting_notes.app session record-stop --capture-id "<capture-id>"
```

Review/export:

```powershell
python -m local_meeting_notes.app review recent --limit 12
python -m local_meeting_notes.app review show --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format html
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
```

Workspace:

```powershell
python -m local_meeting_notes.app session library
python -m local_meeting_notes.app session library --sort oldest --filter review-ready
python -m local_meeting_notes.app session search --query "decision"
python -m local_meeting_notes.app session search --query "decision" --scope decisions
python -m local_meeting_notes.app actions workspace --limit 200
python -m local_meeting_notes.app actions workspace --filter active --sort recent
python -m local_meeting_notes.app actions workspace --filter carried-forward --sort owner
python -m local_meeting_notes.app memory list --item-type decisions
```

The Session Library is a local session browser. It shows the display name first, capture id second, then lifecycle, review/final/export status, timestamps, and compact provider/model metadata when available. The desktop library supports `newest` and `oldest` sorting plus simple filters for all sessions, review-ready sessions, finalised sessions, exported sessions, and sessions needing attention.

Planned sessions are intentionally lightweight in this phase: title, optional planned start time, optional context notes, and a direct start-recording path. Upcoming-meeting creation is also lightweight and currently uses a local/mock provider boundary so future calendar integrations can slot in without redesigning the workflow. This is not calendar sync, reminders, recurrence, attendee management, or a Teams bot.

Ad hoc recording remains the default path. Manual naming/editing always wins over imported/upcoming metadata after a session is created.

Search is also local and SQLite-backed. Results are grouped by session, prefer reviewed/effective extracted content where it exists, hide rejected extracted items, reduce duplicate evidence/content matches, and cap noisy repeats per session. Search scopes are intentionally lightweight: all, sessions, summaries, actions, decisions, blockers/risks, and open questions.

The Global Action Tracker is for follow-through across sessions. It shows actionable `action` and `follow_up` items, keeps source session and owner visible, supports workflow states `open`, `done`, `carried_forward`, and `dismissed`, and can filter active/all/open/done/carried-forward/dismissed items. Sorting is available by most recent, oldest, owner, or source session. Workflow changes are persisted locally in SQLite and survive app restart.

Recording confidence cues in the desktop app show when capture is starting, active, pausing, resuming, stopping, processing locally, ready for review, or needs attention. Pause and stop are cooperative because the app may wait for the current audio chunk to close before changing state or processing saved audio.

## Optional Local LLM Setup

Start Ollama and pull a model:

```powershell
ollama serve
ollama pull llama3.1:8b
python -m local_meeting_notes.app llm check
```

Example `.env` values:

```dotenv
SUMMARY_PROVIDER=local_llm
ACTION_EXTRACTION_PROVIDER=local_llm
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=llama3.1:8b
LOCAL_LLM_TIMEOUT_SECONDS=45
LOCAL_LLM_MAX_TRANSCRIPT_CHARS=12000
```

If Ollama is unavailable, slow, returns invalid JSON, or produces weakly grounded content, the workflow falls back to heuristic behavior rather than failing the whole capture.

## Validation Commands

Backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_session_workflow_service.py -q
```

Frontend build:

```powershell
cd .\app
npm run build
```

Tauri/Rust check:

```powershell
cd .\app\src-tauri
cargo check
```

## Documentation

- Demo guide: [`docs/demo/demo-walkthrough.md`](docs/demo/demo-walkthrough.md)
- Troubleshooting: [`docs/troubleshooting.md`](docs/troubleshooting.md)
- Current status: [`docs/current-status.md`](docs/current-status.md)
- Roadmap: [`docs/roadmap.md`](docs/roadmap.md)
- Windows setup: [`docs/setup/windows-local-dev.md`](docs/setup/windows-local-dev.md)

## Known Limitations

- Audio capture reliability varies by Windows device and driver.
- Microphone-only is the recommended current mode for demos.
- System audio capture remains constrained and should be described honestly.
- Pause/stop can wait briefly for the current chunk to finish writing.
- Processing is local and can take time for transcription, diarization, summaries, and extraction.
- Diarization is generic and imperfect.
- Speaker ownership may remain `Unknown` or `Unconfirmed speaker`.
- Search is SQLite-backed and useful for obvious persisted terms, with lightweight scopes and duplicate cleanup, but not a full-text search product.
- Local LLM output quality depends on runtime health and model choice.
- Human review is expected before sharing exports.
- Reviewed extracted items are protected from destructive re-extraction.

No Teams bot, cloud pipeline, Microsoft auth, or production Outlook integration is implemented.
