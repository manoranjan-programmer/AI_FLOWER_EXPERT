# start.ps1 – Launch the Flower AI Chatbot Microservice on port 8000
$ErrorActionPreference = "Stop"

Write-Host "=== Flower AI Chatbot Service (Port 8000) ===" -ForegroundColor Green

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment…" -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "Starting Chatbot service on http://localhost:8000" -ForegroundColor Green
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
