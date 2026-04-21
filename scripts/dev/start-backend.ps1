$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Python virtual environment not found. Create .venv first."
}

& ".venv\Scripts\python.exe" -m local_meeting_notes.app
