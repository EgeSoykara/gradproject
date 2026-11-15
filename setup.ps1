param([string]$EngineZip)

$ErrorActionPreference = 'Stop'
if ($EngineZip) { $EngineZip = (Resolve-Path -LiteralPath $EngineZip).Path }
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment.' }
}
$python = '.venv/Scripts/python.exe'
$packages = @('-r', 'requirements.txt')
if ($EngineZip) {
    & $python integrations/prepare_engine.py $EngineZip
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the engine package.' }
    $packages += @('-e', '../PortfolioAI_Ege', 'statsmodels==0.15.0', 'tefas-crawler==0.6.0', 'transformers==5.18.0')
}
& $python -m pip install @packages
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.venv/Scripts/python.exe' manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Database setup failed.' }
& '.venv/Scripts/python.exe' manage.py seed_demo --create-account
if ($LASTEXITCODE -ne 0) { throw 'Sample data setup failed.' }
if ($EngineZip) {
    & $python manage.py import_fund_catalog ../PortfolioAI_Ege/data/universe_scores.json
    if ($LASTEXITCODE -ne 0) { throw 'Fund catalog import failed.' }
    & $python manage.py seed_engine_demo
    if ($LASTEXITCODE -ne 0) { throw 'Archive portfolio setup failed.' }
    Write-Host 'Ready. Run .\start.ps1 -Engine and select the archive portfolio after signing in as demo.'
    return
}
& '.venv/Scripts/python.exe' manage.py train_models --dataset demo
if ($LASTEXITCODE -ne 0) { throw 'Model training failed.' }
Write-Host 'Ready. Run .\start.ps1 and open http://127.0.0.1:8000'
