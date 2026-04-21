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

## 5. Run the desktop shell

```powershell
npm run tauri:dev
```

## Notes

- Keep `.env` local and out of source control.
- The backend creates local data folders on startup.
- The current backend uses mock transcript data only.
- Windows loopback capture is practical but fragile on some drivers and devices.
