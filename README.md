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
python -m local_meeting_notes.app transcript transcribe --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript status --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript list --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize run --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize status --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize list --capture-id "<capture-id>"
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>"
python -m local_meeting_notes.app summary show --capture-id "<capture-id>"
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>"
python -m local_meeting_notes.app actions list --capture-id "<capture-id>"
```

### Windows Audio Libraries

The MVP capture path uses:
- `soundcard`: fastest practical route to Windows speaker loopback and microphone capture through WASAPI-backed devices
- `soundfile`: simple `.wav` writing for chunked local files
- `numpy`: frame handling for mono normalization and chunk shaping

This is intentionally pragmatic rather than abstract. Windows loopback capture is still fragile across audio drivers, Bluetooth devices, sample-rate mismatches, and some virtual audio devices.

### Local Transcription Libraries

The MVP transcription path uses:
- `faster-whisper`: practical offline chunk transcription with a clean Python API
- `soundfile`: chunk duration inspection and audio metadata access

The provider is wrapped so we can swap transcription backends later without rewriting the CLI or persistence layer.

### Local Diarization Libraries

The MVP diarization path uses:
- `librosa`: local waveform loading and feature extraction
- `scikit-learn`: offline clustering for generic speaker grouping

This is a practical offline MVP, not a claim of perfect speaker identity. The output is limited to generic labels like `Speaker 1`, `Speaker 2`, and `Speaker 3`.

### Local Summary And Extraction Approach

Phase 6 uses local heuristic services behind swappable provider boundaries:
- `summarizer`: produces an executive summary plus a more detailed topic-oriented summary
- `action_extractor`: extracts decisions, actions, follow-ups, blockers or risks, and open questions

These services are intentionally conservative:
- they rely on transcript evidence instead of inventing certainty
- they use generic ownership such as `Speaker 1`, `Unknown`, or `Unconfirmed speaker`
- they are designed to tolerate imperfect diarization rather than assuming speaker labels are always right

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
- Transcript segments are persisted per chunk in SQLite, including chunk path and failure state.
- Diarization segments are persisted separately and used to apply best-effort generic speaker labels onto transcript rows.
- Summaries, actions, decisions, and follow-ups are persisted in SQLite by `capture_id`.
- Summary and extraction outputs include transcript evidence snippets where practical.
- Ownership may remain `Unknown` or `Unconfirmed speaker` when diarization is weak or missing.
- `audio stop` requests a clean stop and may wait until the current chunk finishes writing.
- System loopback plus microphone capture is best-effort on Windows and may require trying a different output device or sample rate.
- No Teams bot, cloud pipeline, or production capture flow is included.
