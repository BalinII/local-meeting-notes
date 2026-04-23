# AGENTS.md

## Project
Local Meeting Notes

Local-first Windows desktop application for capturing meeting audio, transcribing it, performing basic diarization, generating summaries and extracted outcomes, and reviewing/exporting results through a Tauri desktop shell.

This repo is an internal prototype first, not a production SaaS app.

---

## Product intent

Build a private local meeting note taker that:

- runs locally on Windows
- does not join meetings as a bot or visible participant
- captures microphone and system audio locally
- transcribes captured audio
- performs generic speaker diarization
- generates:
  - executive summary
  - detailed summary
  - actions
  - decisions
  - follow-ups
  - blockers / risks
  - open questions
- supports review and export
- stays conservative when evidence is weak

Accuracy and trust matter more than polish.

---

## Current architecture

### Frontend
- Tauri desktop shell
- Vite/React UI
- lightweight review workflow
- no heavy frontend state architecture unless clearly justified

### Backend
Python backend under:

- `backend/src/local_meeting_notes/`

Primary modules:
- `audio_capture`
- `transcription_engine`
- `diarization_engine`
- `summarizer`
- `action_extractor`
- `export_service`
- `storage`
- `local_llm`
- `microsoft_integration` (placeholder / future)
- `meeting_detector` (future)
- `speaker_attribution` (future)

### Storage
- SQLite for persisted outputs
- local filesystem for captured audio, transcripts, exports, temp files

### Local LLM
- Ollama-first local runtime
- current use is for summaries and, where practical, extraction
- heuristic fallback must remain available

---

## Product boundaries

### In scope
- local capture
- local transcription
- local diarization
- local LLM summaries
- conservative extraction
- review UI
- markdown/html/json export
- human review workflow
- explicit uncertainty

### Out of scope unless explicitly requested
- participant identity mapping
- Microsoft auth implementation
- Outlook/Teams production integration
- any visible meeting bot
- cloud infrastructure
- multi-user features
- enterprise auth
- large frontend redesigns

---

## Hard rules

1. **Local-first always**
   - do not introduce cloud dependencies unless explicitly requested
   - do not move core inference/transcript handling to external services

2. **No meeting bot**
   - do not build or suggest visible meeting attendance/joining as the primary model

3. **Do not fake certainty**
   - use `Unknown` or `Unconfirmed speaker` when ownership is unclear
   - suppress weak outputs instead of presenting them confidently

4. **Preserve fallback paths**
   - local LLM failures must not break the workflow
   - heuristic fallback must stay intact unless explicitly replaced

5. **Do not overbuild**
   - choose the smallest maintainable change that solves the problem
   - do not introduce new frameworks or architectural layers without a strong reason

6. **Show evidence**
   - where summaries/actions/decisions are produced, preserve evidence snippets and timing references where practical

7. **Respect current persistence model**
   - avoid unnecessary schema churn
   - extend the schema only when there is clear value

---

## Current product maturity

This is a working internal prototype.

Current known realities:
- transcription is usable, not perfect
- diarization is heuristic and imperfect
- speaker labels are generic
- local LLM summaries are better than heuristics but still need review
- action extraction may still need fallback depending on local model/runtime performance
- human review remains part of the intended workflow

Design and implementation must reflect that reality.

---

## Preferred development order

Work in this order unless explicitly redirected:

1. capture reliability
2. transcription reliability
3. diarization usefulness
4. summary and extraction quality
5. review workflow
6. export usability
7. human editing / acceptance flow
8. real-meeting validation
9. optional metadata integration
10. optional identity mapping

Do not jump ahead to identity mapping or production integrations before review usability is solid.

---

## Coding guidance

### Backend
- keep modules small and explicit
- prefer straightforward Python over clever abstractions
- keep provider boundaries swappable
- return structured data, not loose blobs
- log failures clearly
- preserve backward compatibility where practical

### Frontend
- keep the UI clean, readable, and low-clutter
- present one coherent executive summary and one coherent detailed summary
- extracted items should be clearly separated by type
- uncertainty should be visible, not hidden
- avoid overcomplicated routing/state patterns

### Prompts / LLM usage
- prefer conservative prompts
- explicitly forbid hallucination
- require evidence-backed extraction
- drop weak/garbled items instead of rewriting them badly
- validate structured output before persisting

---

## File and directory expectations

### Important backend paths
- `backend/src/local_meeting_notes/...`
- `backend/data/audio/`
- `backend/data/transcripts/`
- `backend/data/exports/`
- `backend/data/local_meeting_notes.db`

### Important frontend paths
- `app/src/components/`
- `app/src/lib/`
- `app/src/styles/`
- `app/src-tauri/`

### Root files
- `README.md`
- `.env.example`
- `pytest.ini`
- `AGENTS.md`

---

## Environment assumptions

This repo is primarily developed on:
- Windows 11
- Python virtualenv in `.venv`
- Node.js LTS
- Rust / cargo
- Tauri
- Ollama for local LLM runtime

Assume the user runs commands in PowerShell unless told otherwise.

---

## Commands

### Activate Python venv
```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)