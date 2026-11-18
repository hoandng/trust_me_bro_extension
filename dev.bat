@echo off
setlocal
title Trust Me Bro - Dev Runner
set "ROOT_DIR=%~dp0"

echo ========================================================
echo   Dang khoi dong Trust Me Bro (Backend + Extension)
echo ========================================================

:: 1. Khoi dong Backend FastAPI (tu dong nhan dien .venv neu co)
start "Trust Me Bro - Backend" cmd /k "cd /d "%ROOT_DIR%backend" && (if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat) && uvicorn app.main:app --reload --no-proxy-headers"

:: 2. Khoi dong Extension Vite Watcher
start "Trust Me Bro - Extension" cmd /k "cd /d "%ROOT_DIR%extension" && npm run dev"

echo.
echo [THANH CONG] Backend va Extension da duoc khoi dong trong 2 cua so rieng!
echo - Backend API:  http://127.0.0.1:8000 (Swagger: http://127.0.0.1:8000/docs)
echo - Extension:    Thu muc build tai 'extension\dist'
echo - Trinh duyet:  Nap hoac bam nut Reload tai chrome://extensions/
echo.
timeout /t 5
