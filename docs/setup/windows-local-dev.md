# Windows Local Development

## 1. Create the Python environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .\backend
```

## 2. Install frontend dependencies

```powershell
Set-Location .\app
npm install
```

## 3. Run scaffold entrypoints

```powershell
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
python -m local_meeting_notes.app session start --title "Mock Local Meeting"
python -m local_meeting_notes.app session stop
```

## 4. Run manual audio capture

```powershell
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app audio start
python -m local_meeting_notes.app audio status
python -m local_meeting_notes.app audio stop
```

Notes:
- `audio start` launches a background worker.
- Audio chunks are written into `backend/data/audio/<capture-id>/`.
- `audio stop` is cooperative, so it may finish the current chunk before exiting.
- If loopback capture fails, try `--no-loopback` first to verify microphone capture independently.

## 5. Run local transcription

```powershell
python -m local_meeting_notes.app transcript transcribe --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript status --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript list --capture-id "<capture-id>"
```

Notes:
- The MVP transcription flow is batch-oriented, not streaming.
- `faster-whisper` runs locally and may download model files on first use.
- Chunk failures are persisted in SQLite so you can inspect partial results.

## 6. Run local diarization

```powershell
python -m local_meeting_notes.app diarize run --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize status --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize list --capture-id "<capture-id>"
python -m local_meeting_notes.app transcript list --capture-id "<capture-id>"
```

Notes:
- Diarization is batch/offline and uses generic speaker labels only.
- Transcript-to-speaker alignment is best-effort by timing overlap.
- This tuning pass reduces fragmentation, but imperfect alignment is still expected on noisy audio, overlapping speech, and rapid interruptions.

## 7. Run the desktop shell

```powershell
npm run tauri:dev
```

## Notes

- Keep `.env` local and out of source control.
- The backend creates local data folders on startup.
- The current backend has real local chunk transcription and generic speaker diarization, but no participant identity mapping yet.
- Windows loopback capture is practical but fragile on some drivers and devices.
