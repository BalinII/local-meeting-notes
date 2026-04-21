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
python -m local_meeting_notes.app
npm run dev
```

## 4. Run the desktop shell

```powershell
npm run tauri:dev
```

## Notes

- Keep `.env` local and out of source control.
- The backend creates local data folders on startup.
- The current app is scaffolding only, with placeholder modules.
