@echo off
REM One-shot setup on Windows: Python venv + Streamlit + Ollama + MedPsy 4B.
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ============================================================
echo   QVAC vs Cloud LLMs - Health Test - install (one time)
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 not found. Install from https://www.python.org/downloads/
  exit /b 1
)

echo ==^> 1/3 Python virtualenv + Streamlit...
if not exist ".venv" (
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ==^> 2/3 Ollama + QVAC MedPsy 4B + embedding (~3 GB)...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\setup_medpsy.ps1"
if errorlevel 1 exit /b 1

echo.
echo Installation complete.
echo.
echo   Start dashboard:
echo     - Double-click launch_dashboard.bat
echo     - Or: launch_dashboard.bat
echo.
echo   Public demo (no Ollama):
echo     https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app
echo.
endlocal
