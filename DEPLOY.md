# Deploy gratuito (0 €)

## Opzione A — Streamlit Community Cloud (consigliata)

1. Apri: **[Deploy su Streamlit Cloud](https://share.streamlit.io/deploy?repository=FrancescoAloe91/qvac-vs-cloud-llms-health-test&branch=main&mainModule=app.py)**
2. Accedi con **GitHub** (account gratis)
3. Conferma:
   - Repository: `FrancescoAloe91/qvac-vs-cloud-llms-health-test`
   - Branch: `main`
   - Main file: `app.py`
4. Clic **Deploy** — nessuna carta di credito
5. URL live di questo progetto: **https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app**

**Sulla demo cloud:** incolla cloud + ranking OK; **Run benchmark QVAC** solo in locale (Ollama). Puoi incollare manualmente l’output QVAC generato sul tuo Mac.

---

## Opzione B — Render.com (free tier)

1. [render.com](https://render.com) → Sign up gratis (GitHub)
2. **New** → **Blueprint** → collega questo repo
3. Render legge `render.yaml` e avvia la dashboard
4. URL tipo `https://qvac-health-test.onrender.com`

Stesse limitazioni: niente Ollama sul server cloud.

---

## Locale completo (QVAC live)

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
./install.sh
```

Poi doppio click su **QVAC Dashboard.app** o `./launch_dashboard.sh` → `http://localhost:8501`
