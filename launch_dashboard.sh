#!/bin/bash
# Avvia la dashboard in background e apre Safari (senza terminale visibile).
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

PORT=8501
URL="http://localhost:${PORT}"
LOG="/tmp/qvac-health-test-streamlit.log"
PIDFILE="/tmp/qvac-health-test-streamlit.pid"
OLLAMA_BIN="$PROJECT_DIR/.ollama-bin/Ollama.app/Contents/Resources/ollama"
OLLAMA_ADDR="127.0.0.1:11434"

if [ ! -d ".venv" ]; then
  echo "Prima esecuzione: avvio installazione automatica (venv)..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -q -r requirements.txt
else
  source .venv/bin/activate
fi

if [ ! -x "$OLLAMA_BIN" ]; then
  echo ""
  echo "⚠️  MedPsy non ancora installato. Esegui una tantum:"
  echo "    ./install.sh"
  echo ""
fi

# Start the real local MedPsy engine (Ollama) if it isn't already running.
if [ -x "$OLLAMA_BIN" ] && ! curl -sf -o /dev/null "http://${OLLAMA_ADDR}/api/version" 2>/dev/null; then
  export OLLAMA_HOST="$OLLAMA_ADDR"
  export OLLAMA_MODELS="$PROJECT_DIR/.ollama-models"
  nohup "$OLLAMA_BIN" serve > /tmp/qvac-ollama-serve.log 2>&1 &
  disown
  for _ in $(seq 1 20); do
    curl -sf -o /dev/null "http://${OLLAMA_ADDR}/api/version" 2>/dev/null && break
    sleep 1
  done
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false

open_browser() {
  if [ -d "/Applications/Safari.app" ]; then
    open -a Safari "$URL"
  else
    open "$URL"
  fi
}

# Gia' in esecuzione → apri solo Safari
if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
  open_browser
  exit 0
fi

nohup streamlit run app.py \
  --server.port="${PORT}" \
  --server.headless=true \
  --server.showEmailPrompt=false \
  > "$LOG" 2>&1 &

echo $! > "$PIDFILE"

for _ in $(seq 1 30); do
  if curl -sf -o /dev/null "$URL"; then
    open_browser
    exit 0
  fi
  sleep 1
done

echo "Streamlit non partito. Log: $LOG" >&2
exit 1
