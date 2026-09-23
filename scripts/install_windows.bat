@echo off
title OpenPrint Windows Kurulumu
echo =====================================================
echo         OpenPrint Windows Kurulum ve Baslatici
echo =====================================================
echo.

cd /d "%~dp0\.."

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi! Lutfen python.org adresinden Python yukleyin.
    pause
    exit /b
)

if not exist "venv" (
    echo [1/2] Sanal ortam olusturuluyor...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [2/2] OpenPrint baslatiliyor...
echo Tarayicinizdan http://localhost:5050 adresine girin.
echo.
python -m backend.app
pause
