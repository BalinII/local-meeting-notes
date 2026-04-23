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
python -m local_meeting_notes.app llm check
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>"
python -m local_meeting_notes.app summary show --capture-id "<capture-id>"
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>"
python -m local_meeting_notes.app actions list --capture-id "<capture-id>"
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>" --provider local_llm
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>" --provider local_llm
python -m local_meeting_notes.app review show --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app review update-item --item-type action --item-id 1 --review-status edited --description "Reviewed action text"
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format html
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
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

### Local LLM Runtime

Phase 6C adds a second provider mode alongside the heuristic pipeline:
- `heuristic`
- `local_llm`

The first local LLM runtime is Ollama over its local HTTP API. The implementation uses JSON-only prompting, validates model output before persistence, and falls back to the heuristic provider if the local runtime fails or returns invalid structured output.

The local LLM prompt path now cleans transcript input before sending it to the model. It drops obvious filler/noise fragments, collapses repeated words or phrases, removes common `[inaudible]`-style artifacts, and filters malformed fragments. Model outputs are also checked for useful text and evidence overlap before they are persisted.

### Ollama Setup

Install and run Ollama locally, then pull a practical instruct-capable model:

```powershell
ollama serve
ollama pull llama3.1:8b
```

Recommended config in `.env`:

```dotenv
SUMMARY_PROVIDER=local_llm
ACTION_EXTRACTION_PROVIDER=local_llm
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=llama3.1:8b
LOCAL_LLM_TIMEOUT_SECONDS=45
LOCAL_LLM_MAX_TRANSCRIPT_CHARS=12000
```

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
