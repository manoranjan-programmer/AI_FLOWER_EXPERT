# start.ps1 – Launch the Flower AI Classifier Microservice on port 8001
$ErrorActionPreference = "Stop"

Write-Host "=== Flower AI Classifier Service (Port 8001) ===" -ForegroundColor Green

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment…" -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "Starting Classifier service on http://localhost:8001" -ForegroundColor Green
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
