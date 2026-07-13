@echo off
REM Start Streamlit dashboard + Ollama (Windows), open default browser.
setlocal EnableExtensions
cd /d "%~dp0"

set PORT=8501
set URL=http://localhost:%PORT%

if not exist ".venv" (
  echo First run: creating virtualenv...
  python -m venv .venv
  call ".venv\Scripts\activate.bat"
  pip install -q -r requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)

where ollama >nul 2>&1
if errorlevel 1 (
  if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
  ) else (
    echo.
    echo MedPsy not installed yet. Run install.ps1 once.
    echo.
    goto start_streamlit
  )
) else (
  for /f "delims=" %%i in ('where ollama') do set "OLLAMA_EXE=%%i"
)

set OLLAMA_HOST=127.0.0.1:11434
set OLLAMA_MODELS=%CD%\.ollama-models
curl -sf http://127.0.0.1:11434/api/version >nul 2>&1
if errorlevel 1 (
  start "" /B "%OLLAMA_EXE%" serve
  timeout /t 3 /nobreak >nul
)

:start_streamlit
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false

netstat -ano | findstr ":%PORT% " | findstr LISTENING >nul
if not errorlevel 1 (
  start "" "%URL%"
  exit /b 0
)

start "" /B streamlit run app.py --server.port=%PORT% --server.headless=true --server.showEmailPrompt=false
for /l %%i in (1,1,30) do (
  curl -sf "%URL%" >nul 2>&1 && (
    start "" "%URL%"
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)
echo Streamlit did not start. Check the terminal output.
exit /b 1
