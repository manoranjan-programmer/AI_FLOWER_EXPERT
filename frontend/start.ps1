# start.ps1 – Launch the Flower AI Expert frontend dev server
# Run from the frontend/ directory: .\start.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Flower AI Expert – Frontend ===" -ForegroundColor Green

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies…" -ForegroundColor Cyan
    npm install
}

Write-Host "Starting Vite dev server on http://localhost:5173" -ForegroundColor Green
npm run dev
