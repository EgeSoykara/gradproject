param([switch]$Engine, [ValidateRange(1, 65535)][int]$Port = 8000)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Run .\setup.ps1 first.'
}
if ($Engine) { Write-Host 'Archive analysis is selected from the portfolio menu.' }
Write-Host "PortfolioAI: http://127.0.0.1:$Port/dashboard/ (Ctrl+C to stop)"
& '.venv/Scripts/python.exe' manage.py runserver "127.0.0.1:$Port"
