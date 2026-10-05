@echo off
REM ===================================================================
REM  OpenPrint (Kolay Yazçcç) - Windows Kurulum Betißi
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
title OpenPrint - Kurulum
cd /d "%~dp0"

color 0B

echo ==================================================================
echo    OpenPrint (Kolay Yazçcç) - Windows Kurulum
echo    SÅrÅcÅsÅz, USB Kablolu ve Wi-Fi Evrensel Yazdçrma Sunucusu
echo ==================================================================
echo.

REM ---------------------------------------------------------------------
REM  1) Python bul
REM
REM  Windows 10/11'de `python` komutu áoßu zaman Microsoft Store'un sahte
REM  kçsayoluna gider. Python kurulu deßilse hata 9009 dîner ve
REM  `python --version` hiábir üey yazmaz. Bu yÅzden sçrayla:
REM    - `py -3` denenir (geráek Python kuruluysa her zaman vardçr)
REM    - `python.exe` WindowsApps iáindeyse (Store sahtesi) atlançr
REM    - adayçn geráekten Python 3.10+ oldußu áalçütçrçlarak doßrulançr
REM
REM  Hata seviyesi blok iáinde `if %errorlevel% neq 0` ile DE¶òL
REM  `if errorlevel 1` ile okunur: yÅzde biáimi blok ayrçütçrçlçrken
REM  geniületilir ve yanlçü deßeri okur.
REM ---------------------------------------------------------------------
set "PY="
set "PYVER="

py -3 -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"

if not defined PY (
    for /f "delims=" %%F in ('where python.exe 2^>nul') do (
        if not defined PY (
            echo %%F | findstr /i "WindowsApps" >nul
            if errorlevel 1 (
                python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,10) else 1)" >nul 2>&1
                if not errorlevel 1 set "PY=python"
            )
        )
    )
)

if not defined PY (
    for /f "delims=" %%F in ('where python3.exe 2^>nul') do (
        if not defined PY (
            python3 -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,10) else 1)" >nul 2>&1
            if not errorlevel 1 set "PY=python3"
        )
    )
)

if defined PY (
    for /f "delims=" %%v in ('%PY% --version 2^>nul') do if not defined PYVER set "PYVER=%%v"
)

if not defined PY (
    echo [!] Python 3.10 veya Åzeri bulunamadç. winget ile kuruluyor...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [X] HATA: winget bulunamadç.
        echo.
        echo     https://www.python.org adresinden Python 3.10 veya Åzeri
        echo     sÅrÅmÅ indirip kurun. Kurulum ekrançnda mutlaka
        echo     "Add python.exe to PATH" seáeneßini iüaretleyin.
        echo.
        echo     Not: Windows Ayarlarç ^> Uygulamalar ^> Geliümiü uygulama
        echo     ayarlarç ^> Uygulama yÅrÅtme kçsayollarç bîlÅmÅndeki
        echo     "python.exe" ve "python3.exe" kçsayollarç Store'a yînlendirir
        echo     ve komut satçrçnda `python` áalçümaz.
        echo.
        pause
        exit /b 1
    )
    echo [*] winget ile kuruluyor, bu birkaá dakika sÅrebilir...
    winget install --id Python.Python.3.12 -e --silent --scope user --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [X] HATA: Python kurulamadç.
        echo     LÅtfen https://www.python.org adresinden indirip kurun.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [i] Kurulum tamamlandç. Bu pencereyi kapatçp betißi yeniden
    echo     áalçütçrçn - PATH'in gÅncellenmesi gerekiyor.
    echo.
    pause
    exit /b 2
)

echo [OK] Python bulundu: %PYVER%
echo      komut: %PY%
echo.

REM ---------------------------------------------------------------------
REM  2) Sanal ortam (venv)
REM
REM  `call activate.bat` yerine doßrudan venv yorumlayçcçsç kullançlçyor.
REM  Bîylece PATH deßiüimi yapçlmaz, yol boüluk iáerdißinde sorun áçkmaz ve
REM  sanal ortam geráekten yoksa sessizce devam edilmez.
REM
REM  Eski betik bunu doßrulamçyordu: venv oluüturulamayçnca
REM  `call venv\Scripts\activate.bat` "Sistem belirtilen yolu bulamçyor."
REM  hatasç veriyordu ve kurulum sessizce áîkÅyordu.
REM ---------------------------------------------------------------------
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Python sanal ortamç oluüturuluyor (venv)...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [X] HATA: Sanal ortam oluüturulamadç.
        pause
        exit /b 1
    )
)

if not exist "venv\Scripts\python.exe" (
    echo [X] HATA: venv\Scripts\python.exe oluümadç.
    echo     Bu klasîre yazma izniniz oldußundan emin olun ve betißi
    echo     "Program Files" gibi korumalç bir klasîrde áalçütçrmayçn.
    pause
    exit /b 1
)

set "VENV_PY=%~dp0venv\Scripts\python.exe"

echo [2/3] Gerekli paketler yÅkleniyor (Flask, Pillow, PyPDF)...
"%VENV_PY%" -m pip install --upgrade pip --quiet --disable-pip-version-check
if errorlevel 1 echo [!] pip gÅncellemesi baüarçsçz, mevcut sÅrÅmle devam ediliyor.

"%VENV_PY%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [X] HATA: Paketler kurulamadç. ònternet baßlantçnçzç kontrol edin.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------
REM  3) Baülat
REM ---------------------------------------------------------------------
echo [3/3] OpenPrint baülatçlçyor...
echo.
echo ==================================================================
echo    Yerel eriüim : http://localhost:5050
echo    Yazçcçnçz otomatik olarak algçlançr.
echo    Durdurmak iáin bu pencereyi kapatçn veya Ctrl+C yapçn.
echo ==================================================================
echo.

start "" http://localhost:5050
"%VENV_PY%" -m backend.app

echo.
echo [i] Sunucu durdu.
pause
endlocal
