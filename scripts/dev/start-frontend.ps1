$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..\app")
npm run dev
