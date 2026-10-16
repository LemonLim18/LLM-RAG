$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath "$PSScriptRoot\.venv-m0\Scripts\python.exe")) {
    throw 'CogniShield backend environment is missing. Follow backend/requirements-local.lock.txt setup; no dependencies were installed automatically.'
}
& "$PSScriptRoot\.venv-m0\Scripts\python.exe" "$PSScriptRoot\run_environment.py"
