# Local Meeting Notes

Local Meeting Notes is a Windows-first, local-first desktop app scaffold for capturing meeting context, preparing transcripts, and generating notes without joining meetings as a bot.

Phase 1 focuses on repository structure only:
- Tauri desktop shell scaffold
- Python backend package layout
- SQLite-ready local storage paths
- Placeholder modules for the future meeting pipeline
- Windows-oriented setup and helper scripts

Phase 2 adds a minimal backend skeleton:
- config loading
- logging
- SQLite schema bootstrap
- base record models
- mock meeting session CLI

Phase 3 adds the first real MVP capability:
- Windows-oriented local audio capture
- manual audio start and stop from the CLI
- chunked `.wav` output under `backend/data/audio`
- system loopback plus microphone capture where the local machine supports it

Phase 4 adds the first local transcription pipeline:
- batch transcription of captured audio chunks
- SQLite persistence of transcript chunk metadata and text
- CLI commands to transcribe a capture and inspect transcript segments

Phase 5 adds offline diarization:
- batch speaker-turn segmentation for captured audio
- SQLite persistence of diarization segments
- generic speaker-labelled transcript inspection

Phase 6 adds local summary and extraction:
- executive and detailed summaries generated from persisted transcript segments
- SQLite persistence for summaries, actions, decisions, and follow-ups
- CLI commands to generate and inspect evidence-backed outputs
- conservative ownership handling that tolerates imperfect diarization

Phase 6C adds a local LLM provider option:
- Ollama-first local LLM support for summaries and extraction
- strict JSON output with validation and normalization
- clean heuristic fallback on invalid output, timeout, or runtime failure
- configurable provider selection from config or CLI

Phase 6D tunes local LLM output quality:
- transcript cleaning before prompting to reduce ASR noise
- stricter prompts that tell the model to omit weak or garbled items
- post-processing filters that reject poorly grounded summaries and outcomes
- cleaner meeting-note wording while preserving evidence snippets and timestamps

Phase 7 adds output review and export:
- Markdown, HTML, and JSON exports for persisted capture outputs
- a basic desktop review screen for summaries and extracted items
- visible uncertainty for unknown or unconfirmed ownership
- evidence snippets and provider metadata in review/export views

Phase 8 adds a lightweight human review workflow:
- extracted actions, decisions, follow-ups, risks, and open questions can be accepted, edited, or rejected
- reviewed state is stored locally in SQLite beside the generated output
- exports prefer reviewed text and omit rejected extracted items from Markdown and HTML

Phase 9 adds cross-session memory workspace features:
- dedicated session library view and API payloads for all locally persisted sessions
- cross-session search across display names, summaries, and extracted outcomes
- global action tracker with workflow states (`open`, `done`, `dismissed`, `carried_forward`)
- lightweight finalisation state (`final`) for reviewed sessions
- memory views for decisions, blockers/risks, and open questions

Phase 10 strengthens finalisation and preferred-content selection:
- session finalisation remains lightweight and session-level (`reviewed` -> `final`)
- global views now use one shared preference rule: `final` first, then `reviewed`, then `generated`
- cross-session search ranks by content state (`final` > `reviewed` > `generated`) before recency
- global Actions and Memory support lightweight visibility filters (`Final only`, `Reviewed + Final`, `All content`)
- provenance is preserved through source session ids, names, and lifecycle state in global views and exports

Current stabilization notes:
- The desktop UI is currently a review/export workspace for persisted captures, not a full recording-control dashboard.
- Session recording commands exist in the backend CLI and Tauri command layer, but capture reliability remains a validation focus.
- Reviewed extracted items are protected from destructive re-extraction; re-run extraction only before human review or after intentionally resetting review state.
- Mic and loopback audio are captured as separate source files. Transcription currently expects one source timeline and will reject parallel mic+loopback captures until source mixing/alignment is implemented.

No participant identity mapping, Microsoft auth, or Teams bot logic is implemented.

## Phase 1 Repo Structure

```text
local-meeting-notes/
|-- app/
|   |-- package.json
|   |-- tsconfig.json
|   |-- vite.config.ts
|   |-- index.html
|   |-- src/
|   |   |-- App.tsx
|   |   |-- main.tsx
|   |   |-- env.d.ts
|   |   |-- components/
|   |   |   |-- AppShell.tsx
|   |   |   `-- StatusCard.tsx
|   |   |-- lib/
|   |   |   `-- placeholders.ts
|   |   `-- styles/
|   |       `-- app.css
|   `-- src-tauri/
|       |-- Cargo.toml
|       |-- build.rs
|       |-- tauri.conf.json
|       `-- src/
|           |-- lib.rs
|           `-- main.rs
|-- backend/
|   |-- pyproject.toml
|   |-- data/
|   |   |-- audio/
|   |   |-- exports/
|   |   |-- meetings/
|   |   |-- transcripts/
|   |   `-- tmp/
|   `-- src/
|       `-- local_meeting_notes/
|           |-- app.py
|           |-- config.py
|           |-- bootstrap.py
|           |-- api/
|           |-- core/
|           |-- models/
|           |-- services/
|           |-- utils/
|           |-- meeting_detector/
|           |-- audio_capture/
|           |-- transcription_engine/
|           |-- diarization_engine/
|           |-- speaker_attribution/
|           |-- summarizer/
|           |-- action_extractor/
|           |-- storage/
|           |-- microsoft_integration/
|           `-- export_service/
|-- docs/
|   |-- architecture/
|   |   `-- phase-1-overview.md
|   `-- setup/
|       `-- windows-local-dev.md
|-- scripts/
|   |-- dev/
|   |   |-- start-backend.ps1
|   |   `-- start-frontend.ps1
|   `-- windows/
|       `-- setup-local-env.ps1
|-- tests/
|   |-- integration/
|   |   `-- test_scaffold.py
|   `-- unit/
|       `-- test_bootstrap.py
|-- .env.example
|-- .gitignore
`-- CODEX_TASK_1.md
```

## Placeholder Modules

The backend includes starter packages for:
- `meeting_detector`
- `audio_capture`
- `transcription_engine`
- `diarization_engine`
- `summarizer`
- `action_extractor`
- `storage`
- `export_service`
- `local_llm`

### Data and persistence

- SQLite database for generated/reviewed records
- Local filesystem for audio chunks, transcripts, exports, and temp artifacts

## Prerequisites

- Windows 11 preferred
- Python 3.12+
- Node.js 20+
- Rust stable (MSVC toolchain)
- WebView2 runtime (for Tauri)
- (Optional but recommended) Ollama local runtime for `local_llm` provider

## Quick start (developer)

### 1) Clone and set up Python environment

```powershell
git clone <repo-url>
cd local-meeting-notes
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
pip install -e .\backend
```

### 2) Initialize backend and database

```powershell
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
python -m local_meeting_notes.app session start --title "Mock Local Meeting"
python -m local_meeting_notes.app session stop
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app audio start
python -m local_meeting_notes.app audio status
python -m local_meeting_notes.app audio stop
python -m local_meeting_notes.app transcript transcribe --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript status --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript list --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize run --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize status --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize list --capture-id "<capture-id>"
python -m local_meeting_notes.app llm check
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>"
python -m local_meeting_notes.app summary show --capture-id "<capture-id>"
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>"
python -m local_meeting_notes.app actions list --capture-id "<capture-id>"
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>" --provider local_llm
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>" --provider local_llm
python -m local_meeting_notes.app review recent --limit 12
python -m local_meeting_notes.app review show --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app review update-item --item-type action --item-id 1 --review-status edited --description "Reviewed action text"
python -m local_meeting_notes.app session library
python -m local_meeting_notes.app session search --query "roadmap"
python -m local_meeting_notes.app actions workspace --limit 200
python -m local_meeting_notes.app actions update-workflow --item-type action --item-id 1 --workflow-status carried_forward
python -m local_meeting_notes.app session finalise --capture-id "<capture-id>"
python -m local_meeting_notes.app memory list --item-type decisions
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format html
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
```

### 3) (Optional) Configure Ollama-backed local LLM

Start Ollama and pull a model:

```powershell
ollama serve
ollama pull llama3.1:8b
```

Set `.env` values (example):

```dotenv
SUMMARY_PROVIDER=local_llm
ACTION_EXTRACTION_PROVIDER=local_llm
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=llama3.1:8b
LOCAL_LLM_TIMEOUT_SECONDS=45
LOCAL_LLM_MAX_TRANSCRIPT_CHARS=12000
```

### 4) Run frontend and desktop shell

```powershell
cd .\app
npm install
npm run tauri:dev
```

## Core CLI workflow (backend)

Use these commands from repo root with the Python venv activated.

### Session + audio capture

```powershell
python -m local_meeting_notes.app session start --title "Demo Meeting"
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app audio start
python -m local_meeting_notes.app audio status
python -m local_meeting_notes.app audio stop
python -m local_meeting_notes.app session stop
```

### Transcription + diarization

```powershell
python -m local_meeting_notes.app transcript transcribe --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript list --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize run --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize list --capture-id "<capture-id>"
```

### Summaries + extracted outcomes

```powershell
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>"
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>"
python -m local_meeting_notes.app review show --capture-id "<capture-id>" --format markdown
```

### Review + export

```powershell
python -m local_meeting_notes.app review update-item --item-type action --item-id 1 --review-status edited --description "Reviewed action text"
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format html
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
```

## Testing and checks

From repo root:

```powershell
Set-Location .\app
npm run tauri:dev
```

The desktop shell now opens a lightweight review workspace:
- enter a capture id
- load persisted summaries and extracted outputs
- expand evidence snippets
- edit, save, accept, or reject extracted items
- export Markdown, HTML, or JSON through the local backend

## Notes

- The app is designed for local data storage first.
- SQLite remains the default persistence target.
- Microsoft integration is metadata-oriented only in this scaffold.
- Mock transcript segments are used for the CLI-backed demo flow.
- Audio capture writes timestamped local chunks into `backend/data/audio/<capture-id>/`.
- Transcript segments are persisted per chunk in SQLite, including chunk path and failure state.
- Diarization segments are persisted separately and used to apply best-effort generic speaker labels onto transcript rows.
- Summaries, actions, decisions, and follow-ups are persisted in SQLite by `capture_id`.
- Summary and extraction rows also store provider metadata so you can tell whether the heuristic or local LLM path produced them.
- Summary and extraction outputs include transcript evidence snippets where practical.
- Extracted output rows keep generated text and reviewed text separately, with `generated`, `accepted`, `edited`, or `rejected` review status.
- Markdown and HTML exports use reviewed descriptions and reviewed owner text where present, and skip rejected extracted items.
- JSON exports include generated, reviewed, effective, and review status fields for local inspection.
- Ownership may remain `Unknown` or `Unconfirmed speaker` when diarization is weak or missing.
- `local_llm` currently targets Ollama first, but the client boundary is designed so another local OpenAI-compatible runtime can be swapped in later.
- If Ollama is unreachable, times out, or returns invalid JSON, the app falls back to the heuristic provider instead of failing the whole pipeline.
- If the model output is weak, noisy, or not clearly grounded in evidence, the app omits it or falls back rather than polishing unsupported claims.
- Exports are written under `backend/data/exports/<capture-id>/`.
- The review UI surfaces uncertain ownership with `Unknown` or `Unconfirmed speaker` badges rather than hiding it.
- `audio stop` requests a clean stop and may wait until the current chunk finishes writing.
- System loopback plus microphone capture is best-effort on Windows and may require trying a different output device or sample rate.
- No Teams bot, cloud pipeline, or production capture flow is included.
