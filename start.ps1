$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements.txt first. See README.md.'
}
$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $existing) {
    Start-Process -FilePath $pythonPath -ArgumentList '-m uvicorn src.api.main:app --host 127.0.0.1 --port 8000' -WorkingDirectory $projectPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectPath 'data/api.log') -RedirectStandardError (Join-Path $projectPath 'data/api-error.log')
}
Start-Process 'http://localhost:8000'
