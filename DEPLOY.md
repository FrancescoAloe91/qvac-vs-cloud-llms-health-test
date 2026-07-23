# Free deploy ($0)

## Option A — Streamlit Community Cloud (recommended)

1. Open: **[Deploy on Streamlit Cloud](https://share.streamlit.io/deploy?repository=FrancescoAloe91/qvac-vs-cloud-llms-health-test&branch=main&mainModule=app.py)**
2. Sign in with **GitHub** (free account)
3. Confirm:
   - Repository: `FrancescoAloe91/qvac-vs-cloud-llms-health-test`
   - Branch: `main`
   - Main file: `app.py`
4. Click **Deploy** — no credit card required
5. Live URL for this project: **https://francescoaloe91-qvac-vs-cloud-llms-health-test-app-wihxyd.streamlit.app**

**On the cloud demo:** paste cloud answers + ranking work; **Run benchmark QVAC** only runs locally (Ollama). You can manually paste QVAC output generated on your Mac or Windows PC.

---

## Option B — Render.com (free tier)

1. [render.com](https://render.com) → Sign up free (GitHub)
2. **New** → **Blueprint** → connect this repo
3. Render reads `render.yaml` and starts the dashboard
4. URL looks like `https://qvac-health-test.onrender.com`

Same limits: no Ollama on the cloud host.

---

## Full local setup (live QVAC)

**macOS**

```bash
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
./install.sh
```

Then double-click **QVAC Dashboard.app** or run `./launch_dashboard.sh` → `http://localhost:8501`

**Windows**

```powershell
git clone https://github.com/FrancescoAloe91/qvac-vs-cloud-llms-health-test.git
cd qvac-vs-cloud-llms-health-test
powershell -ExecutionPolicy Bypass -File install.ps1
.\launch_dashboard.bat
```
