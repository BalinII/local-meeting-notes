$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -e .\backend

Write-Host "Backend scaffold environment is ready."
Write-Host "Next: Set-Location .\\app; npm install"
