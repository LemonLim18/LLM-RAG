$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& "$PSScriptRoot\.venv-m0\Scripts\python.exe" "$PSScriptRoot\run_environment.py"
