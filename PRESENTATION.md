# QVAC vs Cloud LLMs — Health Test  
### Pitch one-pager (demo / investors / workshop)

---

## The problem

Clinical data should not leave the device without DPA, consent, and an audit trail — yet clinicians still want LLM assistance. Free cloud models (ChatGPT / Claude / Gemini) are convenient but **expose the case**; paid tiers cost money and still do not solve privacy.

## The proposal

A **transparent comparison** of three cloud LLMs (real answers, pasted manually) against **QVAC MedPsy 4B** running **on-device** on the same clinical prompt — with measured KPIs, not invented scores.

| | Cloud (free tier) | QVAC MedPsy 4B (local) |
|---|---|---|
| Cost per case | $0 (free account) | $0 (CPU, no API) |
| Clinical data | Leaves the device | Stays on-device |
| TTFT / TPS | Not measurable (copy-paste) | Measured in real time |
| Model | General-purpose (varies by account) | Medicine fine-tuned |

## How it works (60 seconds)

1. Pick one of **5 clinical cases** (4 presets + 1 anonymized real case)  
2. Same prompt on ChatGPT, Claude, Gemini  
3. **Run benchmark** → QVAC answers locally (stock Ollama Modelfile settings)  
4. Dashboard: **consensus ranking** (cases 1–4) and **vs gold standard** (case 5)  
5. **Save** per case; case 5 keeps a rolling window of up to **10 runs** and averages them  
6. **Final averaged ranking** + optional anonymized USDT wallet reward simulation  

### Scoring (same rule everywhere)

**40% diagnosis · 30% plan · 20% urgency · 10% summary**  
Continuous 0–100 semantic scores. **Cons.%** is rescaled (#1 = 100%); **Ref.%** vs a confirmed diagnosis is absolute.

## What it proves (and what it does not)

**Yes**

- Prompt parity and an honest comparison (no pre-canned QVAC answers)  
- Privacy by design for QVAC  
- Real workflow: copy-paste cloud answers like a hospital without API integration  
- Local semantic scoring (meaning, not wording alone)

**No**

- Does not prove a 4B beats paid GPT‑4o / Opus  
- Cloud answers are the **free tier** available on official sites  
- Not a medical device and not clinical advice  

## Demo

| Mode | Link / command |
|---|---|
| **Public (free)** | [Live demo](https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app) |
| **Full (live QVAC)** | `git clone` → `./install.sh` (macOS) or `install.ps1` (Windows) → launcher → `http://localhost:8501` |

## Stack

Streamlit · Python · Ollama · MedPsy-4B-GGUF · embedding `all-minilm` · Plotly · zero paid API keys

## Closing line

> *“Same case, same prompt — cloud that exposes the data vs QVAC that stays home. You see the numbers and decide.”*

**Repo:** https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test
