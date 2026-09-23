@echo off
chcp 65001 >nul
title OpenPrint / Kolay Yazıcı - Windows Kurulum ve Başlatıcı
color 0B

echo ==================================================================
echo     🖨️  OpenPrint (Kolay Yazıcı) - Windows 1-Tık Kurulum
echo         Sürücüsüz & PWA Destekli Kişisel Bulut Yazdırma Sunucusu
echo ==================================================================
echo.

cd /d "%~dp0"

:: 1. Python Kontrolü
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python sisteminizde bulunamadı.
    echo [*] Python otomatik olarak kuruluyor... (winget)
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo [HATA] Python kurulamadı! Lütfen https://www.python.org adresinden indirip kurun.
        echo Kurulum sırasında "Add python.exe to PATH" seçeneğini işaretlemeyi unutmayın.
        pause
        exit /b 1
    )
)

:: 2. Sanal Ortam ve Paket Kurulumu
if not exist "venv" (
    echo [1/3] Python sanal ortamı oluşturuluyor (venv)...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/3] Gerekli paketler yükleniyor (Flask, Pillow, PyPDF)...
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [3/3] OpenPrint Başlatılıyor...
echo.
echo ==================================================================
echo   🌐 Yerel Erişim: http://localhost:5050
echo   🖨️ Yazıcınız otomatik olarak algılandı.
echo ==================================================================
echo.

:: Tarayıcıyı otomatik aç
start http://localhost:5050

:: Backend'i çalıştır
python -m backend.app

pause
