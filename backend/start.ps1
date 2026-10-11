# Start the AEMS backend from anywhere. Run: powershell -File backend/start.ps1
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = $repoRoot
if (-not $env:PORT) { $env:PORT = '4174' }
if (-not $env:LOCAL_DEMO_LOGIN) { $env:LOCAL_DEMO_LOGIN = '1' }
Set-Location -LiteralPath $repoRoot
python -u backend/run.py
