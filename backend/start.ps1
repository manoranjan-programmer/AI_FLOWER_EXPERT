# start.ps1 – Launch the Flower AI Expert backend
# Run from the backend/ directory: .\start.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Flower AI Expert – Backend ===" -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment…" -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "No venv found – using system Python." -ForegroundColor Yellow
}

Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
