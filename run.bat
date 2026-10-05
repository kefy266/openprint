@echo off
REM ===================================================================
REM  OpenPrint - Hçzlç baülatçcç
REM  Kurulum yapmaz; sanal ortam yoksa install.bat áaßçrçr.
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
    call "%~dp0install.bat"
    if errorlevel 2 exit /b 0
    if errorlevel 1 exit /b 1
)

set "VENV_PY=%~dp0venv\Scripts\python.exe"
start "" http://localhost:5050
"%VENV_PY%" -m backend.app
endlocal
