# Digital Cafe Pro - PowerShell Start Script
Write-Host "===================================" -ForegroundColor Cyan
Write-Host " Digital Cafe Pro - Start Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Installing Dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install -r requirements.txt -q
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Starting Backend Server (Port 5000)..." -ForegroundColor Yellow
Write-Host ""
python app.py
