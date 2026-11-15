param([switch]$Engine, [ValidateRange(1, 65535)][int]$Port = 8000)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Run .\setup.ps1 first.'
}
$python = '.venv/Scripts/python.exe'
& $python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Could not update the database. Check the migration error above.' }
if ($Engine) { Write-Host 'Archive analysis is selected from the portfolio menu.' }
Write-Host "PortfolioAI: http://127.0.0.1:$Port/dashboard/ (Ctrl+C to stop)"
& $python manage.py runserver "127.0.0.1:$Port"
