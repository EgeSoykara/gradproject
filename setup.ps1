$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment.' }
}
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.venv/Scripts/python.exe' manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Database setup failed.' }
& '.venv/Scripts/python.exe' manage.py seed_demo --create-account
if ($LASTEXITCODE -ne 0) { throw 'Sample data setup failed.' }
& '.venv/Scripts/python.exe' manage.py train_models --dataset demo
if ($LASTEXITCODE -ne 0) { throw 'Model training failed.' }
Write-Host 'Ready. Run .\start.ps1 and open http://127.0.0.1:8000'
