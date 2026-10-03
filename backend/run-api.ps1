param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements.lock.txt first; see README.md.' }
$env:APP_MODE = 'production'
$env:DATA_DIR = Join-Path $PSScriptRoot 'data\production'
& $taskPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
