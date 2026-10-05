#!/usr/bin/env python3
"""
openprint Windows .bat dosyalarını üretir ve denetler.

Kullanım
--------
    python tools/fix_windows_bat.py              # dosyaları yeniden üret
    python tools/fix_windows_bat.py --check      # yalnızca denetle, yazma
    python tools/fix_windows_bat.py --verify-output out.txt   # cmd.exe çıktısını denetle

NEDEN BU KURAL VAR
------------------
cmd.exe bir .bat dosyasını BAYT KONUMUNA göre ayrıştırır. Satır sonu LF
olduğunda satır başına 1 bayt ilerler (CRLF'de 2). Dosyada Türkçe harf
veya emoji gibi çok baytlı değerler bulunduğunda imleç yanlış konuma
kayıyor ve sonraki her komutun BAŞINDAKİ birkaç karakter yutuluyor.
Kullanıcıya göründüğü hâliyle şöyle bir çöp akışı oluşur:

    'ndows' is not recognized as an internal or external command
    'ontrolü' is not recognized as an internal or external command

Bu bir kurulum hatası DEĞİL, dosya kodlamasının belirtisidir. Asıl hata
(kurulum hiç yapılmıyor) ekranın aşağısında kaybolup gidiyor.

cp857 seçildi çünkü Türkçe Windows konsolunun OEM kod sayfası 857'dir:
Türkçe harfler doğru görünür ve hiçbir karakter çok baytlı olmadığı için
ayrıştırma hatasının oluşması mümkün değildir. Türkçe olmayan Windows
kurulumlarında harfler farklı görünür ama hiçbir şey bozulmaz.

Doğru değişken "127 üstü bayt" değil ÇOK BAYTLILIKTIR. cp857 tek baytlık
bir kod sayfası olduğu için dosya cp857'ye çözülebiliyorsa karakter = 1
bayt garantidir ve cmd.exe'nin bayt imleci asla kayamaz. Asıl kırıcı,
satır sonlarının CRLF olmamasıdır.
"""

import pathlib
import sys

OUT = pathlib.Path(__file__).resolve().parent.parent
ENC = "cp857"

RULE = r"""REM  Dosya kuralları (bilerek):
REM    kodlama   : Windows-857 (Türkçe OEM, tek bayt/karakter)
REM    satır sonu: CRLF
REM    BOM yok, chcp yok, emoji yok
REM
REM  Bu kurallar bozulursa cmd.exe satırların başındaki karakterleri
REM  yutar ve şöyle bir çöp akışı görünür:
REM    'ndows' is not recognized as an internal or external command
REM  Bu bir kod hatası değil, kodlama hatasıdır."""


INSTALL = f"""@echo off
REM ===================================================================
REM  OpenPrint (Kolay Yazıcı) - Windows Kurulum Betiği
REM
{RULE}
REM ===================================================================
setlocal EnableExtensions
title OpenPrint - Kurulum
cd /d "%~dp0"

color 0B

echo ==================================================================
echo    OpenPrint (Kolay Yazıcı) - Windows Kurulum
echo    Sürücüsüz, USB Kablolu ve Wi-Fi Evrensel Yazdırma Sunucusu
echo ==================================================================
echo.

REM ---------------------------------------------------------------------
REM  1) Python bul
REM
REM  Windows 10/11'de `python` komutu çoğu zaman Microsoft Store'un sahte
REM  kısayoluna gider. Python kurulu değilse hata 9009 döner ve
REM  `python --version` hiçbir şey yazmaz. Bu yüzden sırayla:
REM    - `py -3` denenir (gerçek Python kuruluysa her zaman vardır)
REM    - `python.exe` WindowsApps içindeyse (Store sahtesi) atlanır
REM    - adayın gerçekten Python 3.10+ olduğu çalıştırılarak doğrulanır
REM
REM  Hata seviyesi blok içinde `if %errorlevel% neq 0` ile DEĞİL
REM  `if errorlevel 1` ile okunur: yüzde biçimi blok ayrıştırılırken
REM  genişletilir ve yanlış değeri okur.
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
    echo [!] Python 3.10 veya üzeri bulunamadı. winget ile kuruluyor...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [X] HATA: winget bulunamadı.
        echo.
        echo     https://www.python.org adresinden Python 3.10 veya üzeri
        echo     sürümü indirip kurun. Kurulum ekranında mutlaka
        echo     "Add python.exe to PATH" seçeneğini işaretleyin.
        echo.
        echo     Not: Windows Ayarları ^> Uygulamalar ^> Gelişmiş uygulama
        echo     ayarları ^> Uygulama yürütme kısayolları bölümündeki
        echo     "python.exe" ve "python3.exe" kısayolları Store'a yönlendirir
        echo     ve komut satırında `python` çalışmaz.
        echo.
        pause
        exit /b 1
    )
    echo [*] winget ile kuruluyor, bu birkaç dakika sürebilir...
    winget install --id Python.Python.3.12 -e --silent --scope user --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [X] HATA: Python kurulamadı.
        echo     Lütfen https://www.python.org adresinden indirip kurun.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [i] Kurulum tamamlandı. Bu pencereyi kapatıp betiği yeniden
    echo     çalıştırın - PATH'in güncellenmesi gerekiyor.
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
REM  `call activate.bat` yerine doğrudan venv yorumlayıcısı kullanılıyor.
REM  Böylece PATH değişimi yapılmaz, yol boşluk içerdiğinde sorun çıkmaz ve
REM  sanal ortam gerçekten yoksa sessizce devam edilmez.
REM
REM  Eski betik bunu doğrulamıyordu: venv oluşturulamayınca
REM  `call venv\\Scripts\\activate.bat` "Sistem belirtilen yolu bulamıyor."
REM  hatası veriyordu ve kurulum sessizce çöküyordu.
REM ---------------------------------------------------------------------
if not exist "venv\\Scripts\\python.exe" (
    echo [1/3] Python sanal ortamı oluşturuluyor (venv)...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [X] HATA: Sanal ortam oluşturulamadı.
        pause
        exit /b 1
    )
)

if not exist "venv\\Scripts\\python.exe" (
    echo [X] HATA: venv\\Scripts\\python.exe oluşmadı.
    echo     Bu klasöre yazma izniniz olduğundan emin olun ve betiği
    echo     "Program Files" gibi korumalı bir klasörde çalıştırmayın.
    pause
    exit /b 1
)

set "VENV_PY=%~dp0venv\\Scripts\\python.exe"

echo [2/3] Gerekli paketler yükleniyor (Flask, Pillow, PyPDF)...
"%VENV_PY%" -m pip install --upgrade pip --quiet --disable-pip-version-check
if errorlevel 1 echo [!] pip güncellemesi başarısız, mevcut sürümle devam ediliyor.

"%VENV_PY%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [X] HATA: Paketler kurulamadı. İnternet bağlantınızı kontrol edin.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------
REM  3) Başlat
REM ---------------------------------------------------------------------
echo [3/3] OpenPrint başlatılıyor...
echo.
echo ==================================================================
echo    Yerel erişim : http://localhost:5050
echo    Yazıcınız otomatik olarak algılanır.
echo    Durdurmak için bu pencereyi kapatın veya Ctrl+C yapın.
echo ==================================================================
echo.

start "" http://localhost:5050
"%VENV_PY%" -m backend.app

echo.
echo [i] Sunucu durdu.
pause
endlocal
"""


LAUNCHER = f"""@echo off
REM ===================================================================
REM  OpenPrint (Kolay Yazıcı) - Tek Tık Başlatıcı
REM
{RULE}
REM ===================================================================
setlocal EnableExtensions
title OpenPrint
cd /d "%~dp0"

if not exist "venv\\Scripts\\python.exe" (
    echo [!] Sanal ortam bulunamadı, kurulum başlatılıyor...
    echo.
    call "%~dp0install.bat"
    if errorlevel 2 (
        echo.
        echo [i] Kurulum tamamlandı. Pencereyi kapatıp tekrar çalıştırın.
        pause
        exit /b 0
    )
    if errorlevel 1 exit /b 1
)

set "VENV_PY=%~dp0venv\\Scripts\\python.exe"

echo OpenPrint başlatılıyor: http://localhost:5050
echo Durdurmak için bu pencereyi kapatın veya Ctrl+C yapın.
echo.

start "" http://localhost:5050
"%VENV_PY%" -m backend.app

echo.
echo [i] Sunucu durdu.
pause
endlocal
"""


RUNBAT = f"""@echo off
REM ===================================================================
REM  OpenPrint - Hızlı başlatıcı
REM  Kurulum yapmaz; sanal ortam yoksa install.bat çağırır.
REM
{RULE}
REM ===================================================================
setlocal EnableExtensions
title OpenPrint
cd /d "%~dp0"

if not exist "venv\\Scripts\\python.exe" (
    call "%~dp0install.bat"
    if errorlevel 2 exit /b 0
    if errorlevel 1 exit /b 1
)

set "VENV_PY=%~dp0venv\\Scripts\\python.exe"
start "" http://localhost:5050
"%VENV_PY%" -m backend.app
endlocal
"""


SCRIPTS = f"""@echo off
REM ===================================================================
REM  OpenPrint - scripts\\ klasörü içindeki kurulum giriş noktası
REM
REM  Gerçek iş mantığı kök dizindeki install.bat dosyasındadır; burada
REM  yalnızca yönlendirilir, böylece iki kopyası bakım gerektirmez.
REM
{RULE}
REM ===================================================================
cd /d "%~dp0.."
call "%~dp0..\\install.bat"
exit /b %errorlevel%
"""


TARGETS = [
    ("install.bat", INSTALL),
    ("baslat.bat", LAUNCHER),
    ("run.bat", RUNBAT),
    ("scripts/install_windows.bat", SCRIPTS),
]

# cmd.exe tarafından tam ayrıştırılması gereken metinler.
EXPECTED = [
    "Yazıcı",
    "Sürücüsüz, USB Kablolu ve Wi-Fi Evrensel Yazdırma Sunucusu",
    "winget bulunamadı",
    "https://www.python.org",
    "Add python.exe to PATH",
]


def emit(name, text):
    """Metni cp857 + CRLF olarak yaz. Satır sonları her zaman CRLF olur."""
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    data = body.encode(ENC, errors="strict").replace(b"\n", b"\r\n")
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def audit(p):
    """Dosyanın kurallara uyduğunu doğrula. Sorunları listeler."""
    data = p.read_bytes()
    problems = []

    if data[:3] == b"\xef\xbb\xbf":
        problems.append("UTF-8 BOM var (ilk komut bozulur)")
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        problems.append("UTF-16 BOM var")

    bare = data.replace(b"\r\n", b"").count(b"\n")
    if bare:
        problems.append(f"{bare} adet yalnız-LF satır sonu var "
                        f"(cmd.exe satır başını yer, komutlar bozulur)")

    try:
        text = data.decode(ENC)
    except UnicodeDecodeError as e:
        problems.append(f"cp857 çözülemiyor: {e}")
        text = ""

    if text:
        for i, line in enumerate(text.split("\r\n"), 1):
            if any(0x1F000 <= ord(c) <= 0x1FAFF or ord(c) > 0xFFFF for c in line):
                problems.append(f"satır {i}: emoji/çok baytlı işaret kalmış")
                break

    if b"\x00" in data:
        problems.append("dosya içinde NUL baytı var")

    # Yanlış kalıp: blok içinde %errorlevel% genişletmesi.
    if p.suffix.lower() == ".bat" and p.name != "install_windows.bat":
        for i, line in enumerate(text.split("\r\n"), 1):
            if "%errorlevel%" in line.lower() and line.strip().lower().startswith("if "):
                problems.append(f"satır {i}: blok içinde %errorlevel% kullanılmış, "
                                f"'if errorlevel N' kullanılmalı")
    return problems


def verify_output(path):
    """cmd.exe'den alınan çıktının doğru ayrıştırıldığını denetle."""
    raw = pathlib.Path(path).read_bytes()
    text = raw.decode(ENC, errors="replace")
    problems = []

    if "is not recognized" in text:
        problems.append("ayrıştırma hatası: komut parçası çalıştırılmış")

    for probe in EXPECTED:
        if probe not in text:
            problems.append(f"beklenen metin eksik: {probe!r}")

    # Kesilmiş satır belirtileri: mesaj yarıda kalmış.
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Sürücüsüz") and "Sunucusu" not in s:
            problems.append(f"kesilmiş satır: {s!r}")
        if "kuruluyor" in s and "winget" in s and not s.rstrip().endswith("..."):
            problems.append(f"kesilmiş satır: {s!r}")

    return problems, text


def main():
    args = set(sys.argv[1:])
    check_only = "--check" in args
    verify = [a for a in sys.argv[1:] if a.startswith("--verify-output=")]

    rc = 0

    if verify:
        for spec in verify:
            path = spec.split("=", 1)[1]
            problems, text = verify_output(path)
            print(f"cmd.exe çıktı denetimi: {path}")
            if problems:
                for p in problems:
                    print("  !", p)
                rc = 1
            else:
                print(f"  TAMAM ({len(text.splitlines())} satır, tam ayrıştırıldı)")
        return rc

    print(f"{'dosya':30s} {'bayt':>6s} {'CRLF':>5s}  denetim")
    print("-" * 74)
    for name, text in TARGETS:
        p = OUT / name
        if not check_only:
            p = emit(name, text)
        if not p.exists():
            print(f"{name:30s} {'':6s} {'':5s}  HATA (dosya yok)")
            rc = 1
            continue
        problems = audit(p)
        data = p.read_bytes()
        crlf = data.count(b"\r\n")
        print(f"{name:30s} {len(data):6d} {crlf:5d}  "
              f"{'TAMAM' if not problems else 'HATA'}")
        for prob in problems:
            print(f"{'':30s} {'':6s} {'':5s}  ! {prob}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
