# Local Meeting Notes

Local Meeting Notes is a **Windows-first, local-first desktop prototype** for meeting capture and note generation.

It captures local audio (microphone + system loopback when available), transcribes it, applies generic speaker diarization, generates conservative summaries/extracted outcomes, and supports local review and export through a Tauri desktop shell.

> This repository is an internal prototype, not a production SaaS platform.

## What this product is

- **Private-by-default local workflow**: audio, transcripts, summaries, and exports stay on the local machine.
- **No visible meeting bot**: the app does not join meetings as a participant.
- **Human-in-the-loop notes**: generated outputs are intended for review/edit before sharing.
- **Conservative extraction strategy**: weak ownership or unclear evidence is surfaced as `Unknown` or `Unconfirmed speaker`.

## Current capabilities (prototype)

- Local audio capture to chunked `.wav` files.
- Offline transcription pipeline for captured audio.
- Generic speaker diarization (e.g., `Speaker 1`, `Speaker 2`).
- Summary generation:
  - executive summary
  - detailed summary
- Outcome extraction:
  - actions
  - decisions
  - follow-ups
  - blockers/risks
  - open questions
- Provider modes for summary/extraction:
  - `heuristic`
  - `local_llm` (Ollama-first)
- Automatic fallback to heuristic mode when local LLM output is invalid, weak, or unavailable.
- Review/edit/accept/reject workflow for extracted items.
- Export formats: Markdown, HTML, JSON.

## Current status and maturity

This project is in **working internal prototype** stage.

### Reasonably usable now

- Local end-to-end flow from capture -> transcript -> summarize/extract -> review -> export.
- Conservative handling of uncertain ownership.
- Local persistence in SQLite and filesystem-backed artifacts.

### Not production-ready

- Speaker identity is heuristic and generic (no identity mapping).
- Transcription and diarization quality vary by meeting conditions and devices.
- Local LLM quality depends on runtime/model availability.
- Windows capture reliability can vary by driver, sample-rate, and device combinations.
- No cloud sync, multi-user collaboration, enterprise auth, or production Microsoft integration.

### Fallback behavior (important)

- If the local LLM path is unreachable, times out, returns invalid JSON, or provides weak output, the pipeline falls back to `heuristic` provider behavior instead of failing the entire workflow.

For a detailed maturity breakdown, see [`docs/current-status.md`](docs/current-status.md).

For a demo-focused walkthrough, see [`docs/demo/demo-walkthrough.md`](docs/demo/demo-walkthrough.md).

For known issues and remediation guidance, see [`docs/troubleshooting.md`](docs/troubleshooting.md).

## Architecture snapshot

### Frontend

- Tauri desktop shell
- Vite + React UI
- Lightweight review workspace

### Backend

Python package in `backend/src/local_meeting_notes/` with modules including:

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
# backend tests
python -m pytest

# backend lint (if installed)
python -m ruff check backend/src tests

# frontend typecheck/build
cd .\app
npm run build
```

If environment dependencies are missing, see [`docs/troubleshooting.md`](docs/troubleshooting.md).

## Demo readiness resources

- **Walkthrough**: [`docs/demo/demo-walkthrough.md`](docs/demo/demo-walkthrough.md)
- **Troubleshooting**: [`docs/troubleshooting.md`](docs/troubleshooting.md)

## Known limitations and near-term roadmap

### Known limitations (current)

- Accuracy depends on local audio quality and device setup.
- Diarization labels are generic and can be wrong.
- Local LLM output quality varies by model and runtime state.
- Review remains required for high-trust outcomes.

### Near-term priorities

1. Capture reliability
2. Transcription reliability
3. Diarization usefulness
4. Summary/extraction quality
5. Review workflow polish
6. Export usability
7. Real-meeting validation

## Repository highlights

- Backend package: `backend/src/local_meeting_notes/`
- Tauri shell: `app/src-tauri/`
- React UI: `app/src/`
- Local data artifacts: `backend/data/`
- Setup guidance: `docs/setup/windows-local-dev.md`
