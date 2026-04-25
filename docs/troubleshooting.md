# Troubleshooting Guide

This guide covers common setup and runtime issues for the Local Meeting Notes prototype.

## 1) Python / virtual environment issues

### Symptom

- `ModuleNotFoundError: No module named 'local_meeting_notes'`
- CLI commands fail even though code exists.

### Likely cause

- venv not activated
- backend package not installed in editable mode
- wrong Python interpreter on PATH

### Fix

```powershell
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
python -m pip install --upgrade pip
pip install -e .\backend
python -m local_meeting_notes.app --help
```

If `python` still points to a global interpreter, run `.\.venv\Scripts\python.exe -m local_meeting_notes.app --help`.

---

## 2) Git / GitHub sync issues

### Symptom

- local branch behind remote
- non-fast-forward push rejected
- confusing merge state before demo work

### Fix (safe default)

```powershell
git status
git fetch origin
git rebase origin/<your-branch>
```

If you have conflicts:

```powershell
git status
# resolve files

git add <resolved-files>
git rebase --continue
```

If you need to abort rebase:

```powershell
git rebase --abort
```

Tip: keep doc-only changes isolated in a small branch to reduce conflicts with active implementation work.

---

## 3) Ollama connectivity or timeout issues

### Symptom

- `llm check` fails
- summary/extraction local LLM runs hang or timeout
- connection refused on `127.0.0.1:11434`

### Likely cause

- Ollama server not running
- model not pulled
- timeout too short for machine/model

### Fix

```powershell
ollama serve
ollama pull llama3.1:8b
python -m local_meeting_notes.app llm check
```

Verify `.env` values:

```dotenv
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=llama3.1:8b
LOCAL_LLM_TIMEOUT_SECONDS=45
```

If your machine is slower, increase timeout.

---

## 4) Local LLM fallback behavior (expected behavior)

### What happens

If local LLM output is invalid/weak or runtime is unavailable, the app falls back to heuristic provider behavior.

### What to do

- This is usually not a crash condition.
- Continue workflow and review heuristic outputs.
- If you need deterministic behavior, run commands with `--provider heuristic`.

---

## 5) Tauri / Node / Rust build issues

### Symptom

- `npm run tauri:dev` fails
- Rust compilation errors for desktop shell
- missing WebView/runtime errors

### Fix checklist

```powershell
cd .\app
npm install
npm run dev
npm run tauri:dev
```

Also verify:

- Rust stable toolchain with MSVC target installed.
- WebView2 runtime installed on Windows.
- Node.js LTS (20+) in use.

If frontend build fails, run:

```powershell
npm run build
```

to surface type/build issues before Tauri launch.

---

## 6) Missing icon/build asset issues

### Symptom

- Tauri build complains about missing icon resources.
- packaging step fails due to asset path errors.

### Fix

- Confirm expected icon files exist in `app/src-tauri/icons/`.
- Avoid moving/removing icon files without updating `tauri.conf.json`.
- Re-run `npm run tauri:dev` after restoring assets.

If assets were changed by another branch, re-sync and resolve before packaging.

---

## 7) Audio capture issues

### Symptom

- no audio files written
- only mic or only loopback captured
- choppy/empty chunks

### Likely cause

- unsupported/unstable Windows audio device combo
- sample-rate mismatch or virtual/Bluetooth device quirks
- permissions/device selection issues

### Fix checklist

```powershell
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app audio start
python -m local_meeting_notes.app audio status
python -m local_meeting_notes.app audio stop
```

Then:

- switch default Windows input/output device and retry
- test with wired headset/speakers instead of Bluetooth
- reduce other apps using exclusive audio access
- verify chunks are appearing under `backend/data/audio/<capture-id>/`

---

## 8) Export / review UI issues

### Symptom

- capture loads but review content appears empty
- edits not visible in exports
- markdown/html export missing expected rows

### Checks

```powershell
python -m local_meeting_notes.app review show --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
```

Interpretation tips:

- rejected items are intentionally omitted from markdown/html exports
- reviewed text overrides generated text when present
- empty output can mean extraction produced weak/filtered results

---

## 9) Common Windows-specific gotchas

- PowerShell execution policy blocks venv activation scripts.
- Long path or permission quirks when running from protected directories.
- Antivirus can occasionally quarantine build artifacts.
- Running multiple audio-heavy apps can degrade capture reliability.
- Device hot-swaps during capture can produce partial chunks.

Recommended habits:

- run from a normal user directory
- keep paths short/simple
- avoid changing audio device mid-capture
- close unnecessary media/conferencing apps before recording

---

## 10) Quick health check commands

Run these before demos:

```powershell
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app llm check
cd .\app; npm run build
```

If any command fails, resolve it before live demo flow.
