$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot 'backend\.venv-m0\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'The existing backend runtime is missing. No packages were installed.' }
& $python -B backend/scripts/dev_local.py
exit $LASTEXITCODE
