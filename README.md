# QVAC vs Cloud LLMs — Health Test

Dashboard di benchmark clinico: confronta **ChatGPT**, **Claude** e **Gemini** (risposte incollate dai siti ufficiali) con **Tether QVAC MedPsy 4B** in inferenza locale reale via Ollama.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=FrancescoAloe91/qvac-vs-cloud-llms-health-test&branch=main&mainModule=app.py)

**Demo pubblica (gratuita):** vedi [DEPLOY.md](DEPLOY.md) — deploy in 2 minuti su Streamlit Cloud (0 €).

| | Locale (completo) | Cloud pubblica (gratis) |
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

### Setup motore QVAC (una tantum)

```bash
./scripts/setup_medpsy.sh
```

Scarica Ollama, il GGUF di [MedPsy-4B](https://huggingface.co/qvac/MedPsy-4B-GGUF) (~2.7 GB) e il modello embedding `all-minilm-cpu`.

### Dashboard

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Oppure doppio click su **QVAC Dashboard.app** → `http://localhost:8501`

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
4. Ripeti run + salva fino a **4/4** (ogni run QVAC può variare leggermente)  
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

Hosting **100% free** su [Streamlit Community Cloud](https://streamlit.io/cloud) (nessuna carta di credito).

### Deploy in 2 minuti (una tantum)

1. Clicca il badge **“Open in Streamlit”** in cima a questo README (o [deploy diretto](https://share.streamlit.io/deploy?repository=FrancescoAloe91/qvac-vs-cloud-llms-health-test&branch=main&mainModule=app.py))  
2. Accedi con GitHub (account gratis)  
3. Conferma repo `FrancescoAloe91/qvac-vs-cloud-llms-health-test`, branch `main`, file `app.py`  
4. **Deploy** → ottieni URL tipo `https://qvac-vs-cloud-llms-health-test.streamlit.app`

### Cosa funziona sulla demo cloud

- Presentazione UI, casi clinici, incolla cloud, ranking e slot  
- Puoi **incollare manualmente** anche la risposta QVAC (generata sul tuo Mac con `./run.sh`)  
- **Run benchmark** live richiede Ollama → solo in **locale**

Aggiorna il link pubblico nel README dopo il primo deploy. Guida passo-passo: **[DEPLOY.md](DEPLOY.md)**.

---

## Struttura progetto

```
app.py                 # Dashboard Streamlit
lib/                   # cases, medpsy, metrics, diagnosis_compare, session_store, …
PRESENTATION.md        # Pitch one-pager (demo / slide)
scripts/setup_medpsy.sh
launch_dashboard.sh
QVAC Dashboard.app
```

---

## Continuare da un altro PC

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/setup_medpsy.sh
./run.sh
```

I modelli GGUF **non** sono nel repo (`.gitignore`) — `setup_medpsy.sh` li scarica gratis.

---

## Disclaimer

Solo benchmark dimostrativo. Non sostituisce il parere di un medico.
