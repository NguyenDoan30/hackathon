param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements.lock.txt first; see README.md.' }
$env:APP_MODE = 'demo'
$env:DATA_DIR = Join-Path $PSScriptRoot 'data\demo'
Write-Output "Demo: http://127.0.0.1:$Port/demo"
Write-Output "Swagger: http://127.0.0.1:$Port/docs"
& $taskPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
