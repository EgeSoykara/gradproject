$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Run .\setup.ps1 first.'
}
Write-Host 'PortfolioAI: http://127.0.0.1:8000 (Ctrl+C to stop)'
& '.venv/Scripts/python.exe' manage.py runserver 127.0.0.1:8000
