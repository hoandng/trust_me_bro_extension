# Script chay song song Backend va Extension tren PowerShell
$rootDir = $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Dang khoi dong Trust Me Bro (Backend + Extension)    " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Khoi dong Backend FastAPI trong cua so PowerShell moi
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$rootDir\backend'; if (Test-Path .venv\Scripts\Activate.ps1) { .\.venv\Scripts\Activate.ps1 }; uvicorn app.main:app --reload --no-proxy-headers"

# 2. Khoi dong Extension Watcher (Vite) trong cua so PowerShell moi
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$rootDir\extension'; npm run dev"

Write-Host ""
Write-Host "[THANH CONG] Da mo 2 cua so Backend va Extension Watcher!" -ForegroundColor Green
Write-Host "- Backend API:  http://127.0.0.1:8000 (Swagger: http://127.0.0.1:8000/docs)"
Write-Host "- Extension:    Thu muc build tai 'extension\dist'"
Write-Host "- Trinh duyet:  Nap hoac bam nut Reload tai chrome://extensions/"
Write-Host ""
