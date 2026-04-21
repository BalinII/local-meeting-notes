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

No real transcription, Microsoft auth, or Teams bot logic is implemented.

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
- `speaker_attribution`
- `summarizer`
- `action_extractor`
- `storage`
- `microsoft_integration`
- `export_service`

Each package exposes a stub service and clear docstrings so Phase 2 can add implementation without reshaping the repo.

## Local Development Setup

### Prerequisites

- Windows 11 preferred
- Python 3.12+
- Node.js 20+
- Rust stable with MSVC toolchain
- WebView2 runtime

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .\backend
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
python -m local_meeting_notes.app session start --title "Mock Local Meeting"
python -m local_meeting_notes.app session stop
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app audio start
python -m local_meeting_notes.app audio status
python -m local_meeting_notes.app audio stop
```

### Windows Audio Libraries

The MVP capture path uses:
- `soundcard`: fastest practical route to Windows speaker loopback and microphone capture through WASAPI-backed devices
- `soundfile`: simple `.wav` writing for chunked local files
- `numpy`: frame handling for mono normalization and chunk shaping

This is intentionally pragmatic rather than abstract. Windows loopback capture is still fragile across audio drivers, Bluetooth devices, sample-rate mismatches, and some virtual audio devices.

### Frontend

```powershell
Set-Location .\app
npm install
npm run dev
```

### Tauri Desktop Shell

```powershell
Set-Location .\app
npm run tauri:dev
```

## Notes

- The app is designed for local data storage first.
- SQLite remains the default persistence target.
- Microsoft integration is metadata-oriented only in this scaffold.
- Mock transcript segments are used for the CLI-backed demo flow.
- Audio capture writes timestamped local chunks into `backend/data/audio/<capture-id>/`.
- `audio stop` requests a clean stop and may wait until the current chunk finishes writing.
- System loopback plus microphone capture is best-effort on Windows and may require trying a different output device or sample rate.
- No Teams bot, cloud pipeline, or production capture flow is included.
