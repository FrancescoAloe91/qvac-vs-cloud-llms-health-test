#!/bin/bash
# Ferma la dashboard in background.
PIDFILE="/tmp/qvac-health-test-streamlit.pid"
PORT=8501

if [ -f "$PIDFILE" ]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"
fi

pkill -f "streamlit run app.py" 2>/dev/null || true
lsof -ti ":${PORT}" | xargs kill 2>/dev/null || true
pkill -f "Ollama.app/Contents/Resources/ollama serve" 2>/dev/null || true

echo "Dashboard fermata."
