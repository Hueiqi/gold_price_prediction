$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$tunnelPath = Join-Path $projectPath 'tools\cloudflared.exe'
if (-not (Test-Path -LiteralPath $tunnelPath)) {
    throw 'Install the official cloudflared executable at tools/cloudflared.exe first.'
}
$health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health'
if ($health.service -ne 'gold-price-prediction-api') { throw 'Start Auric with start.ps1 first.' }
Write-Host 'The public URL appears below. Keep this terminal and computer running. Press Ctrl+C to stop sharing.'
& $tunnelPath tunnel --url http://127.0.0.1:8000 --no-autoupdate
