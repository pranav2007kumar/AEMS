$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonRuntime = 'C:/Users/prana/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH = "$PSScriptRoot/.deps;$repoRoot"
if (-not $env:PORT) { $env:PORT = '4174' }
Set-Location -LiteralPath $repoRoot
& $pythonRuntime -u backend/run.py
