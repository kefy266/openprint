@echo off
cd /d "%~dp0"
if not exist "venv" (
    call install.bat
) else (
    call venv\Scripts\activate.bat
    start http://localhost:5050
    python -m backend.app
)
