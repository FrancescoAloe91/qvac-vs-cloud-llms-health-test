# QVAC vs Cloud LLMs — Health Test

Clinical benchmark dashboard: compare **ChatGPT**, **Claude**, and **Gemini** (answers pasted from their official free sites) with **Tether QVAC MedPsy 4B** running real on-device inference via Ollama.

**Live demo (free):** [francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app](https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=FrancescoAloe91/qvac-vs-cloud-llms-health-test&branch=main&mainModule=app.py)

| | Local (full) | [Cloud demo](https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app) (free) |
|---|---|---|
| UI + ranking + saved slots | ✅ | ✅ |
| Paste cloud answers | ✅ | ✅ |
| **Run benchmark** QVAC live | ✅ Ollama | ❌ *(paste QVAC output manually)* |
| Semantic embeddings | ✅ Ollama | ⚠️ keyword-only if Ollama is unavailable |
| Cost | **$0** | **$0** |

---

## Benchmark honesty

- **Same clinical prompt** is copied to every cloud site and used for QVAC.
- **No fabricated answers**: if Ollama is unreachable, QVAC shows an error — it never invents a diagnosis.
- **Cloud = free tier** of your account (chatgpt.com, claude.ai, gemini.google.com). This is not a paid GPT‑4o / Claude Opus comparison unless you paste answers from those tiers.
- **QVAC** = medicine-specialized 4B on-device model — a fair edge on clinical cases, not a claim of supremacy over all commercial LLMs.
- **Stock QVAC sampling**: the dashboard does **not** override temperature / seed / top‑k. Ollama uses the Modelfile defaults from setup (`temperature 0.6`, `top_k 20`, `top_p 0.95`).

---

## Local setup (your machine, free)

### New Mac — one-shot install

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
chmod +x install.sh
./install.sh
```

### New Windows PC — one-shot install

```powershell
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
powershell -ExecutionPolicy Bypass -File install.ps1
```

Then start with **`launch_dashboard.bat`** (or `run.bat` for a debug window).

Windows requirements: **Python 3.10+**, **Ollama** (installed automatically via winget when available).

The install script does everything once:

1. **Python** — creates `.venv` and installs Streamlit + dependencies  
2. **Ollama + MedPsy** — downloads the local engine and [MedPsy-4B](https://huggingface.co/qvac/MedPsy-4B-GGUF) (~2.7 GB) + embedding model `all-minilm-cpu`  
3. **Launcher** — rebuilds `QVAC Dashboard.app` with relative paths (works from any folder)

> No separate “QVAC SDK” is required: this project uses **Ollama** + the **MedPsy GGUF** from Hugging Face, managed by `scripts/setup_medpsy.sh` / `scripts/setup_medpsy.ps1`.

### One-click start (after install)

**macOS**

- **Double-click** `QVAC Dashboard.app` → opens Safari at `http://localhost:8501`  
- or: `./launch_dashboard.sh`  
- or: `./run.sh` (foreground, debug)

**Windows**

- Double-click `launch_dashboard.bat`  
- or: `run.bat` (foreground, debug)

### Manual setup (alternative)

```bash
./scripts/setup_medpsy.sh   # Ollama + MedPsy only
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

---

## Benchmark flow

1. **Left sidebar** → load case 1–5 (slot) or recall a saved result  
2. Optional: **Gold standard** (case 5) — confirmed diagnosis for absolute clinical scoring  
3. **Copy prompt** → paste into ChatGPT, Claude, Gemini (free tier of your account)  
4. **Run benchmark** → QVAC MedPsy generates locally (similar but not identical each run)  
5. **Paste** the three cloud answers into their cards  
6. **Save** in the results area → green slot in the sidebar  

### Case 5 — up to 10 runs + rolling average

1. Fill the anonymized real-patient template  
2. Paste cloud answers **once** (you can keep the same cloud texts)  
3. **Run benchmark** → **Save run**  
4. Repeat run + save up to **10/10** (rolling window: last 10 runs; QVAC wording can shift slightly)  
5. Sidebar → **Final averaged ranking** (average of cases 1–4 + gold case 5)

### Reset

- **Reset** (sidebar): clears current work, **keeps** saved slots  
- **Reset saved results**: deletes snapshots only  

---

## KPIs and scoring

**One weighting rule** for both consensus and clinical (gold) scores:

**40% diagnosis · 30% plan & next steps · 20% urgency · 10% clinical summary**

Each dimension is a continuous **0–100** score from local semantic embeddings (meaning, not copy-paste wording).

- **Cases 1–4 (no confirmed diagnosis):** **Cons.%** — inter-model agreement, then **rescaled so #1 = 100%**.  
- **Case 5 (with gold standard):** **Ref.%** — absolute match vs your confirmed reference (**not** rescaled).  

Use **“See exactly how every score was calculated”** under the ranking for the full numeric breakdown.

Privacy (0 = cloud paste / 100 = on-device) is informational only and is **not** part of Cons.% or Ref.%.

---

## Public dashboard (free)

**Live URL:** https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app

Hosted **100% free** on [Streamlit Community Cloud](https://streamlit.io/cloud) (no credit card).

### What works on the cloud demo

- UI, clinical cases, paste cloud answers, ranking and slots  
- You can also **manually paste** a QVAC answer (generated on your machine with the local launcher)  
- Live **Run benchmark** needs Ollama → **local only**

To redeploy or use Render, see **[DEPLOY.md](DEPLOY.md)**.

---

## Project layout

```
app.py                 # Streamlit dashboard
lib/                   # cases, medpsy, metrics, diagnosis_compare, session_store, …
install.sh / install.ps1
PRESENTATION.md        # Pitch one-pager
DEPLOY.md              # Free hosting notes
scripts/setup_medpsy.sh / setup_medpsy.ps1
scripts/verify_score_formulas.py
launch_dashboard.sh / launch_dashboard.bat
QVAC Dashboard.app     # macOS launcher
```

---

## Continue on another Mac or Windows PC

| OS | Install | Start |
|---|---|---|
| **macOS** | `./install.sh` | `QVAC Dashboard.app` or `./launch_dashboard.sh` |
| **Windows** | `install.ps1` | `launch_dashboard.bat` |

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
```

### Cloud model version labels (ChatGPT / Claude / Gemini)

Sidebar → **Cloud model versions** — or edit `data/cloud_tiers.json`.  
Labels appear on model cards, charts, and the ranking table.

### Annotate existing screenshots

Add a top bar (case + tiers) without re-capturing:

```bash
pip install pillow   # once
# put PNGs in assets/screenshots/raw/ and update assets/screenshots/manifest.json
python scripts/annotate_screenshots.py
```

Output lands in `assets/screenshots/annotated/`.

---

## Disclaimer

Demo benchmark only. Not medical advice and not a substitute for a clinician.
