@echo off
cd /d "%~dp0"
if not exist ".venv" (
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
pip install -q -r requirements.txt
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false
echo.
echo Starting QVAC vs Cloud LLMs - Health Test...
echo Open http://localhost:8501 if the browser does not open.
echo.
streamlit run app.py --server.showEmailPrompt=false
