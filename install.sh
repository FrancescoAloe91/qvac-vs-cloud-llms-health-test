#!/usr/bin/env bash
# One-shot setup on a new Mac: Python venv + Streamlit deps + Ollama + MedPsy 4B + embeddings.
# After this, use ./launch_dashboard.sh or double-click QVAC Dashboard.app.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  QVAC vs Cloud LLMs — Health Test · install (one time)       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 non trovato. Installa Python 3.10+ (python.org o: brew install python3)"
  exit 1
fi

echo "==> 1/3 Python virtualenv + Streamlit..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "==> 2/3 Ollama + QVAC MedPsy 4B + embedding (download ~3 GB, gratis)..."
chmod +x scripts/setup_medpsy.sh
./scripts/setup_medpsy.sh

echo "==> 3/3 Launcher one-click (QVAC Dashboard.app)..."
chmod +x run.sh launch_dashboard.sh stop_dashboard.sh install.sh
if [ -x scripts/build_dashboard_app.sh ]; then
  ./scripts/build_dashboard_app.sh
fi

echo ""
echo "✅ Installazione completata."
echo ""
echo "   Avvio con un click:"
echo "     · doppio click su «QVAC Dashboard.app»"
echo "     · oppure: ./launch_dashboard.sh"
echo ""
echo "   Demo pubblica (senza Ollama):"
echo "     https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app"
echo ""
