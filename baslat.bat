@echo off
REM ===================================================================
REM  OpenPrint (Kolay Yazçcç) - Tek Tçk Baülatçcç
REM
REM  Dosya kurallarç (bilerek):
REM    kodlama   : Windows-857 (TÅrkáe OEM, tek bayt/karakter)
REM    satçr sonu: CRLF
REM    BOM yok, chcp yok, emoji yok
REM
REM  Bu kurallar bozulursa cmd.exe satçrlarçn baüçndaki karakterleri
REM  yutar ve üîyle bir áîp akçüç gîrÅnÅr:
REM    'ndows' is not recognized as an internal or external command
REM  Bu bir kod hatasç deßil, kodlama hatasçdçr.
REM ===================================================================
setlocal EnableExtensions
title OpenPrint
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [!] Sanal ortam bulunamadç, kurulum baülatçlçyor...
    echo.
    call "%~dp0install.bat"
    if errorlevel 2 (
        echo.
        echo [i] Kurulum tamamlandç. Pencereyi kapatçp tekrar áalçütçrçn.
        pause
        exit /b 0
    )
    if errorlevel 1 exit /b 1
)

set "VENV_PY=%~dp0venv\Scripts\python.exe"

echo OpenPrint baülatçlçyor: http://localhost:5050
echo Durdurmak iáin bu pencereyi kapatçn veya Ctrl+C yapçn.
echo.

start "" http://localhost:5050
"%VENV_PY%" -m backend.app

echo.
echo [i] Sunucu durdu.
pause
endlocal
