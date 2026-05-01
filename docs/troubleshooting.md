# Troubleshooting Guide

This guide covers common setup, recording, processing, search, and workflow issues for the Local Meeting Notes prototype.

## Quick Health Check

Run from repo root:

```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app llm check
cd .\app
npm run build
```

If a demo is imminent, also keep a known-good `capture_id` ready.

## Python And Virtual Environment Issues

Symptoms:

- `ModuleNotFoundError: No module named 'local_meeting_notes'`
- CLI commands fail from repo root.
- App shell cannot run backend commands.

Fix:

```powershell
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
python -m pip install --upgrade pip
pip install -e .\backend
python -m local_meeting_notes.app --help
```

If `python` resolves to the wrong interpreter, use:

```powershell
.\.venv\Scripts\python.exe -m local_meeting_notes.app --help
```

## Recording Start Issues

Symptoms:

- New recording immediately fails.
- No audio chunks are written.
- App reports startup or active-capture mismatch.

Checks:

```powershell
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app audio status
```

Try:

- use microphone-only mode for the demo
- confirm Windows microphone privacy permissions
- close other audio-heavy apps
- avoid Bluetooth devices if capture is unstable
- switch Windows default input device and retry
- verify chunks under `backend/data/audio/<capture-id>/`

## Pause, Resume, Stop Issues

Symptoms:

- Pause waits longer than expected.
- Resume does not restart capture.
- Stop and Process feels slow.
- Session remains in `processing` or `processing_failed`.

What is normal:

- Pause/stop may wait for the current chunk to finish writing.
- Stop and Process can take time because transcription, diarization, summary, and extraction run locally.
- Processing speed depends on machine, audio length, model size, and local LLM health.

Checks:

```powershell
python -m local_meeting_notes.app session get --capture-id "<capture-id>"
python -m local_meeting_notes.app audio status
python -m local_meeting_notes.app transcript status --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize status --capture-id "<capture-id>"
```

If processing fails, inspect `last_error` in the session payload and retry with a shorter known-good capture.

## Microphone-Only Vs System Audio

Current recommended mode:

- microphone-only for live demos and validation

System audio / loopback realities:

- Windows loopback support depends on drivers and active output devices.
- Bluetooth and virtual devices can be unreliable.
- Parallel mic plus loopback creates separate source timelines.
- The pipeline should not pretend parallel sources are a single aligned transcript until mixing/alignment is implemented.

Safe workaround:

- capture/process one source timeline for the trusted demo flow
- describe system audio as constrained and under validation

## Local LLM Timeout Or Fallback

Symptoms:

- `llm check` fails.
- Summary or extraction takes a long time.
- Output appears heuristic even when `local_llm` is configured.

Checks:

```powershell
ollama serve
ollama pull llama3.1:8b
python -m local_meeting_notes.app llm check
```

Relevant `.env` values:

```dotenv
SUMMARY_PROVIDER=local_llm
ACTION_EXTRACTION_PROVIDER=local_llm
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=llama3.1:8b
LOCAL_LLM_TIMEOUT_SECONDS=45
LOCAL_LLM_MAX_TRANSCRIPT_CHARS=12000
```

Expected fallback behavior:

- If Ollama is unreachable, times out, returns invalid JSON, or produces weakly grounded output, the app falls back to heuristic provider behavior.
- This is intentional and should not be treated as data loss.
- Human review remains required either way.

## Search Behavior And Limits

Symptoms:

- `All` returns results, but a scoped search returns fewer or no results.
- A term appears in raw transcript content but not in summaries or extracted-item scopes.
- Search result count feels lower than expected.

Current behavior:

- Search is local and SQLite-backed.
- It is intended for obvious persisted terms, speaker labels, item labels, session names, and capture ids.
- Results are grouped by session and capped per session so repeated evidence snippets do not dominate the view.
- Reviewed or edited extracted content is preferred over generated wording where available.
- Rejected extracted items are suppressed.
- Available scopes are `all`, `sessions`, `summaries`, `actions`, `decisions`, `blockers-risks`, and `open-questions`.
- Search is not a full-text ranking engine.

Manual checks:

```powershell
python -m local_meeting_notes.app session search --query "Ben"
python -m local_meeting_notes.app session search --query "decision"
python -m local_meeting_notes.app session search --query "decision" --scope decisions
python -m local_meeting_notes.app session search --query "local-first"
python -m local_meeting_notes.app session library
python -m local_meeting_notes.app session library --sort newest --filter needs-attention
```

If a scoped search appears empty, broaden the scope to `all` and confirm the content type. Transcript-only wording may not appear under summaries, actions, decisions, blockers/risks, or open questions.

## Review And Export Issues

Symptoms:

- Capture loads but review content is empty.
- Export misses a reviewed item.
- Re-extraction refuses to run.

Checks:

```powershell
python -m local_meeting_notes.app review recent --limit 12
python -m local_meeting_notes.app review show --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
```

Interpretation:

- Rejected items are intentionally omitted from Markdown and HTML.
- Reviewed text is preferred over generated text where present.
- JSON is the best inspection format for generated/reviewed/effective fields.
- Re-extraction after review is blocked to avoid erasing accepted/edited/rejected work.

## Tauri, Node, And Rust Issues

Symptoms:

- `npm run tauri:dev` fails.
- `npm run build` fails.
- Rust compilation errors.
- Missing WebView2 runtime.

Fix checklist:

```powershell
cd .\app
npm install
npm run build
npm run tauri:dev
```

Verify:

- Node.js 20+
- Rust stable with MSVC toolchain
- WebView2 runtime installed
- backend venv exists at repo root
- backend package installed with `pip install -e .\backend`

For Rust-only validation:

```powershell
cd .\app\src-tauri
cargo check
```

## Missing Icon Or Build Asset Issues

Symptoms:

- Tauri build complains about missing icons.
- Packaging fails because an asset path is missing.

Fix:

- confirm expected icon files exist under `app/src-tauri/icons/`
- avoid moving/removing Tauri assets without updating `tauri.conf.json`
- re-run `npm run tauri:dev`

## Git And GitHub Workflow Issues

Symptoms:

- push rejected
- branch behind remote
- accidental merge conflict before demo
- doc branch conflicts with active implementation branch

Safe default:

```powershell
git status
git fetch origin
git rebase origin/<branch-name>
```

Conflict flow:

```powershell
git status
# edit conflicted files
git add <resolved-files>
git rebase --continue
```

Abort if needed:

```powershell
git rebase --abort
```

Practical advice:

- Keep doc-only changes separate from backend/search/session workflow work.
- Avoid rebasing over active uncommitted changes.
- Run `git status` before and after every demo-prep change.

## Windows-Specific Gotchas

- PowerShell execution policy can block venv activation.
- Protected folders can cause path or permission errors.
- Antivirus may slow or quarantine build artifacts.
- Audio device hot-swaps during recording can produce partial chunks.
- Multiple conferencing/media apps can compete for audio devices.

Recommended habits:

- work from a normal user project directory
- keep paths short
- use a wired microphone for demos where possible
- avoid changing audio devices mid-recording
- close unnecessary audio apps before capture
