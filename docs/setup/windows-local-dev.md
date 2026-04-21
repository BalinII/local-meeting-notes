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

## 4. Run the desktop shell

```powershell
npm run tauri:dev
```

## Notes

- Keep `.env` local and out of source control.
- The backend creates local data folders on startup.
- The current backend uses mock transcript data only.
