# QVAC vs Cloud LLMs — Health Test  
### Pitch one-pager (demo / investitori / workshop)

---

## Il problema

I dati clinici non possono uscire dal dispositivo senza DPA, consenso e audit trail — ma i medici vogliono comunque l’aiuto dei LLM. I modelli cloud gratuiti (ChatGPT / Claude / Gemini) sono comodi ma **espongono il caso**; i tier premium costano e non risolvono la privacy.

## La proposta

**Confronto trasparente** tra tre LLM cloud (risposte reali, incollate manualmente) e **QVAC MedPsy 4B** che gira **in locale** sullo stesso prompt clinico — con KPI misurati, non inventati.

| | Cloud (free tier) | QVAC MedPsy 4B (locale) |
|---|---|---|
| Costo per caso | 0 € (account free) | 0 € (CPU, no API) |
| Dato clinico | Esce dal dispositivo | Resta on-device |
| TTFT / TPS | Non misurabile (copy-paste) | Misurato in tempo reale |
| Modello | Generico (varia per account) | Fine-tuned medicina |

## Come funziona (60 secondi)

1. Scegli uno di **5 casi clinici** (4 standard + 1 reale anonimizzato)  
2. Stesso prompt su ChatGPT, Claude, Gemini  
3. **Run benchmark** → QVAC risponde in locale  
4. Dashboard: **ranking consenso** (casi 1–4) e **vs gold standard** (caso 5)  
5. **Salva** per caso; caso 5 fino a **4 run** con media  
6. **Ranking definitivo mediato** + simulazione wallet USDT (reward anonimizzato)

## Cosa dimostra (e cosa no)

**Sì**

- Parità di prompt e confronto onesto (nessuna risposta QVAC precompilata)  
- Privacy by design per QVAC  
- Workflow reale: copy-paste cloud come in ospedale senza integrazione API  
- Scoring semantico locale (significato, non solo parole)

**No**

- Non prova che un 4B batte GPT‑4o / Opus a pagamento  
- I cloud sono il **tier gratuito** che l’utente ha sui siti ufficiali  
- Non è dispositivo medico né consulenza clinica

## Demo

| Modalità | Link / comando |
|---|---|
| **Pubblica (gratis)** | Deploy Streamlit Community Cloud — badge nel [README](README.md) |
| **Completa (QVAC live)** | `git clone` → `./scripts/setup_medpsy.sh` → `./run.sh` → `http://localhost:8501` |

## Stack

Streamlit · Python · Ollama · MedPsy-4B-GGUF · embedding `all-minilm` · Plotly · zero API key a pagamento

## Chiusura

> *“Stesso caso, stesso prompt — cloud che espone il dato vs QVAC che resta in casa. Tu vedi i numeri e decidi.”*

**Repo:** https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test
