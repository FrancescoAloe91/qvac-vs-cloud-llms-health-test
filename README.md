# QVAC vs Cloud LLMs - Health Test

Medical LLM & VLM Benchmark Dashboard con Tokenomics.

Confronta tre modelli Cloud (risposte incollate manualmente dai siti ufficiali)
contro il **vero** [qvac/MedPsy-4B](https://huggingface.co/qvac/MedPsy-4B) di
Tether AI Research, eseguito in locale via Ollama — non una risposta
precompilata. VLM, tokenomics USDT e confronto diagnostico automatico incluso.

**Onestà del benchmark**: QVAC non ha "armi" diverse dagli altri modelli. Gira
per davvero sullo stesso prompt identico incollato su ChatGPT/Claude/Gemini,
con TTFT/TPS/latenza misurati per davvero (non simulati). Se il motore locale
non è raggiungibile, la dashboard mostra un errore chiaro — non inventa mai
una risposta.

## Setup del motore locale (una tantum)

```
./scripts/setup_medpsy.sh
```

Scarica Ollama (senza Homebrew), il file GGUF quantizzato di MedPsy-4B da
Hugging Face (~2.7 GB) e crea il modello locale `medpsy-4b-cpu`. Vedi
`lib/medpsy.py` per i dettagli di runtime (host/modello configurabili via
`QVAC_OLLAMA_HOST` / `QVAC_OLLAMA_MODEL`).

## Avvio senza terminale

Doppio click su **QVAC Dashboard.app** → Safari apre `http://localhost:8501`
(`launch_dashboard.sh` avvia anche il motore Ollama locale se non è già attivo)

Bookmark consigliato: `http://localhost:8501`

Fermare: `./stop_dashboard.sh`

## Flusso benchmark

1. Scegli **tier** (Light / Medium / Premium) — stesso livello di analisi per tutti e 3 i cloud
2. Opzionale: spunta **Apri siti nel browser**
3. **Copia prompt** dall'expander e incollalo manualmente su ChatGPT, Claude, Gemini
4. Clicca **Esegui Benchmark** → QVAC MedPsy genera la diagnosi in locale
5. **Incolla** le 3 risposte cloud nei riquadri editabili
6. **Ricalcola confronto diagnostico** — tutti e 4 i modelli nei KPI

### Reset

Il pulsante **Reset** in sidebar azzera tutto, **wallet incluso (0.00 USDT)**.

### KPI

| Modello | Performance TTFT/TPS | Diagnosi |
|---------|---------------------|----------|
| Cloud (3 siti) | Non misurabile | Incolla manualmente |
| QVAC MedPsy 4B | Misurato per davvero (Ollama, CPU) | Inferenza reale, streaming live + chain-of-thought |

Il confronto **Affidabilità** e **Accuratezza (consenso)** include tutti e 4 i modelli
a parità di prompt.

## Struttura

```
app.py
lib/  cases, medpsy, metrics, browser, diagnosis_compare, wallet, vlm, reset
QVAC Dashboard.app
launch_dashboard.sh
```

### Punteggi (KPI)

Tre segnali reali, calcolati dal testo incollato — mai stimati o inventati:

1. **Affidabilità** — overlap tra la diagnosi differenziale di un modello e quella di ogni altro modello (lista + parole chiave).
2. **Accuratezza (consenso)** — quanto la diagnosi primaria di un modello combacia con le parole chiave su cui la maggioranza converge.
3. **Similarità semantica** — somiglianza di *significato* (non solo di parole) tra le diagnosi primarie, calcolata da un piccolo embedding model locale (`all-minilm`, via Ollama, CPU-only). Se il motore locale non è raggiungibile questo terzo segnale viene semplicemente omesso, con un avviso in dashboard — non viene mai inventato un numero.

Il **punteggio finale** (0-100) è una media pesata dei tre segnali sopra. Se viene fornita una diagnosi di riferimento, compare anche un **voto clinico 1-10** con una rubrica dedicata. Ogni singolo numero è ispezionabile dal pulsante **"See exactly how every score was calculated"** sotto la classifica.

## Continuare lo sviluppo da un altro PC

Questo progetto è su GitHub. Per riprendere il lavoro da un'altra macchina con Cursor:

```bash
git clone https://github.com/<tuo-utente>/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/setup_medpsy.sh   # una tantum: scarica Ollama + MedPsy-4B + embedding model
./run.sh                    # avvia la dashboard su http://localhost:8501
```

Nota: il modello GGUF di MedPsy (~2.7 GB) e i binari di Ollama **non** sono nel repo (sono in `.gitignore`) — li scarica `setup_medpsy.sh` la prima volta, su ogni macchina.

## Disclaimer

Solo benchmark dimostrativo. Non sostituisce il parere di un medico.
