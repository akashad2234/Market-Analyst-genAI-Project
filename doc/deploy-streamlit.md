# Deploy AI Market Analyst to Streamlit Cloud

## Overview

The project includes a **standalone** Streamlit app (`app.py`) that runs analysis locally without a separate API server. This is ideal for deployment on [Streamlit Community Cloud](https://share.streamlit.io).

## Deployment Steps

### 1. Push to GitHub

Ensure your code is pushed to a GitHub repository:

```bash
git add .
git commit -m "Add standalone Streamlit app for deployment"
git push origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository: `akashad2234/Market-Analyst-genAI-Project`
5. Set **Main file path**: `app.py`
6. Set **Branch**: `main`
7. Click **"Deploy!"**

### 3. Environment Variables (Optional)

If you use LLM-powered narratives (Google Gemini), add these in Streamlit Cloud **Settings → Secrets**:

```toml
GOOGLE_API_KEY = "your-api-key"
LLM_ENABLED = "true"
LLM_MODEL = "gemini-1.5-flash"
```

For database/cache (SQLite):

```toml
DB_PATH = "data/market_analyst.db"
CACHE_TTL_ANALYSIS = "900"
```

> **Note:** Streamlit Cloud has ephemeral storage. SQLite data will not persist across app restarts. For persistent cache, use an external database.

### 4. App URL

After deployment, Streamlit Cloud provides a URL like:

```
https://<your-app-name>.streamlit.app
```

## File Structure

| File | Purpose |
|------|---------|
| `app.py` | Standalone Streamlit app (deploy this) |
| `ui/streamlit_app.py` | Streamlit app that calls FastAPI (for local dev) |
| `requirements.txt` | Python dependencies (used by Streamlit Cloud) |
| `.streamlit/config.toml` | Streamlit server config |

## Local Run

To run the standalone app locally:

```bash
streamlit run app.py
```

Or with the Makefile:

```bash
make dev-ui-standalone
```

(Add this target if needed.)
