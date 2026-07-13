# QVAC vs Cloud LLMs — Health Test

Dashboard di benchmark clinico: confronta **ChatGPT**, **Claude** e **Gemini** (risposte incollate dai siti ufficiali) con **Tether QVAC MedPsy 4B** in inferenza locale reale via Ollama.

**Demo live (gratis):** [francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app](https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=FrancescoAloe91/qvac-vs-cloud-llms-health-test&branch=main&mainModule=app.py)

| | Locale (completo) | [Demo cloud](https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app) (gratis) |
|---|---|---|
| UI + ranking + slot salvati | ✅ | ✅ |
| Incolla risposte cloud | ✅ | ✅ |
| **Run benchmark** QVAC live | ✅ Ollama | ❌ *(incolla output QVAC a mano)* |
| Embedding semantico | ✅ Ollama | ⚠️ solo keyword se Ollama assente |
| Costo | **0 €** | **0 €** |

---

## Onestà del benchmark

- **Stesso prompt clinico** copiato su tutti i siti cloud e usato per QVAC.
- **Nessuna risposta inventata**: se Ollama non risponde, QVAC mostra errore — non simula mai un risultato.
- **Cloud = tier gratuito** del tuo account (chatgpt.com, claude.ai, gemini.google.com). Non è un confronto con GPT‑4o / Claude Opus a pagamento unless you paste answers from those tiers.
- **QVAC** = modello medico specializzato 4B on-device — vantaggio legittimo su casi clinici, non prova di supremazia su tutti i LLM commerciali.

---

## Avvio locale (macchina tua, tutto gratis)

### Nuova Mac — installazione one-shot

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
chmod +x install.sh
./install.sh
```

### Nuovo PC Windows — installazione one-shot

```powershell
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
powershell -ExecutionPolicy Bypass -File install.ps1
```

Poi avvia con **`launch_dashboard.bat`** (oppure `run.bat` per debug in finestra).

Requisiti Windows: **Python 3.10+**, **Ollama** (installato automaticamente via winget se disponibile).

Lo script fa tutto in automatico (una tantum):

1. **Python** — crea `.venv` e installa Streamlit + dipendenze  
2. **Ollama + MedPsy** — scarica il motore locale e il modello [MedPsy-4B](https://huggingface.co/qvac/MedPsy-4B-GGUF) (~2.7 GB) + embedding `all-minilm-cpu`  
3. **Launcher** — ricostruisce `QVAC Dashboard.app` con path relativi (funziona in qualsiasi cartella)

> Non serve un “QVAC SDK” separato: il progetto usa **Ollama** + **MedPsy GGUF** da Hugging Face, gestiti da `scripts/setup_medpsy.sh` (chiamato da `install.sh`).

### Avvio con un click (dopo l’install)

**macOS**

- **Doppio click** su `QVAC Dashboard.app` → apre Safari su `http://localhost:8501`  
- oppure: `./launch_dashboard.sh`  
- oppure: `./run.sh` (foreground, debug)

**Windows**

- Doppio click su `launch_dashboard.bat`  
- oppure: `run.bat` (foreground, debug)

### Setup manuale (alternativa)

```bash
./scripts/setup_medpsy.sh   # solo motore Ollama + MedPsy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

---

## Flusso benchmark

1. **Sidebar sinistra** → carica caso 1–5 (slot) o richiama risultato salvato  
2. Opzionale: **Gold standard** (caso 5) — diagnosi certa per punteggio clinico semantico  
3. **Copia prompt** → incolla su ChatGPT, Claude, Gemini (tier free del tuo account)  
4. **Run benchmark** → QVAC MedPsy genera in locale (risposta simile ma non identica a ogni run)  
5. **Incolla** le 3 risposte cloud nei riquadri  
6. **Salva** nell’area risultati (main) → slot verde in sidebar  

### Caso 5 — fino a 4 run + media

1. Compila il template del caso reale anonimizzato  
2. Incolla cloud **una volta** (puoi tenere le stesse risposte)  
3. **Run benchmark** → **Salva run 1/4**  
4. Ripeti run + salva fino a **10/10** (finestra rolling: ultime 10 run; ogni run QVAC può variare leggermente)  
5. Sidebar → **Ranking definitivo mediato** (media casi 1–4 + gold caso 5)

### Reset

- **Reset** (sidebar): azzera lavoro corrente, **mantiene** slot salvati  
- **Reset risultati salvati**: cancella solo gli snapshot  

---

## KPI e punteggi

**Casi 1–4 (senza diagnosi certa):** punteggio di **consenso** — accordo tra modelli (affidabilità + accuratezza keyword + similarità semantica locale).

**Caso 5 (con gold standard):** punteggio **clinico semantico** vs diagnosi di riferimento (diagnosi, piano, urgenza).

Pulsante **“Vedi come sono calcolati i punteggi”** sotto la classifica per il dettaglio.

---

## Dashboard pubblica (gratuita)

**URL live:** https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app

Hosting **100% free** su [Streamlit Community Cloud](https://streamlit.io/cloud) (nessuna carta di credito).

### Cosa funziona sulla demo cloud

- Presentazione UI, casi clinici, incolla cloud, ranking e slot  
- Puoi **incollare manualmente** anche la risposta QVAC (generata sul tuo Mac con `./launch_dashboard.sh`)  
- **Run benchmark** live richiede Ollama → solo in **locale**

Per rifare il deploy o usare Render: **[DEPLOY.md](DEPLOY.md)**.

---

## Struttura progetto

```
app.py                 # Dashboard Streamlit
lib/                   # cases, medpsy, metrics, diagnosis_compare, session_store, …
install.sh             # Setup one-shot nuova Mac (venv + MedPsy + launcher)
PRESENTATION.md        # Pitch one-pager (demo / slide)
scripts/setup_medpsy.sh
scripts/build_dashboard_app.sh
launch_dashboard.sh
QVAC Dashboard.app
```

---

## Continuare da un altro PC / nuova Mac o Windows

| Sistema | Comando install | Avvio |
|---|---|---|
| **macOS** | `./install.sh` | `QVAC Dashboard.app` o `./launch_dashboard.sh` |
| **Windows** | `install.ps1` | `launch_dashboard.bat` |

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
```

### Etichette versione cloud (ChatGPT / Claude / Gemini)

In sidebar → **Versioni modelli cloud** — oppure modifica `data/cloud_tiers.json`.  
Le etichette compaiono su schede modello, grafici e tabella ranking.

### Screenshot già fatti — solo intestazione

Per aggiungere una barra in alto (caso + tier usati) senza rifare lo screenshot:

```bash
pip install pillow   # una tantum
# copia i PNG in assets/screenshots/raw/ e aggiorna assets/screenshots/manifest.json
python scripts/annotate_screenshots.py
```

Output in `assets/screenshots/annotated/`.

---

## Disclaimer

Solo benchmark dimostrativo. Non sostituisce il parere di un medico.
