# Deployment Guide

## Prerequisites

- Python 3.11+ (3.14 tested)
- Docker and Docker Compose (for containerised deployment)
- A valid `GEMINI_API_KEY` from Google AI Studio

---

## Environment Variables

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in values.

### Required

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |

### Optional

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `google` | LLM provider (`google`, `openai`, etc.) |
| `LLM_MODEL` | `gemini-2.0-flash` | Model name |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature |
| `FUNDAMENTAL_WEIGHT` | `0.4` | Fundamental agent weight in final score |
| `TECHNICAL_WEIGHT` | `0.4` | Technical agent weight in final score |
| `SENTIMENT_WEIGHT` | `0.2` | Sentiment agent weight in final score |
| `SCORING_THRESHOLDS` | `[[80,"Strong Buy"],[60,"Buy"],[40,"Hold"],[0,"Avoid"]]` | JSON array of score thresholds |
| `YAHOO_HISTORY_PERIOD_DAYS` | `365` | Days of historical data to fetch |
| `YAHOO_HISTORY_INTERVAL` | `1d` | Candle interval |
| `DDG_MAX_RESULTS` | `10` | Max news articles per search |
| `DDG_RATE_LIMIT_SECONDS` | `1.5` | Min seconds between DuckDuckGo requests |
| `DDG_CACHE_SIZE` | `128` | LRU cache entries for search results |
| `API_HOST` | `0.0.0.0` | FastAPI bind host |
| `API_PORT` | `8000` | FastAPI bind port |
| `CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Option 1: Local Development

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
make install

# Configure
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Run API server (port 8000)
make dev-api

# Run Streamlit UI (port 8501) in a separate terminal
make dev-ui
```

---

## Option 2: Docker Compose (Recommended for Deployment)

```bash
# Configure
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Build and start both services
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f api
docker compose logs -f ui

# Stop
docker compose down
```

Services:
- **API**: http://localhost:8000 (health check: `/health`, metrics: `/metrics`)
- **UI**: http://localhost:8501

---

## Option 3: Individual Docker Containers

### Backend API only

```bash
docker build -t market-analyst-api .
docker run -d \
  --name market-analyst-api \
  -p 8000:8000 \
  --env-file .env \
  market-analyst-api
```

### Streamlit UI only

```bash
docker build -f Dockerfile.ui -t market-analyst-ui .
docker run -d \
  --name market-analyst-ui \
  -p 8501:8501 \
  -e API_BASE=http://host.docker.internal:8000 \
  market-analyst-ui
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check, returns `{"status": "ok"}` |
| `GET` | `/metrics` | Live metrics (counters, latencies, errors) |
| `POST` | `/analyze_stock` | Analyse a single stock |
| `POST` | `/portfolio_analysis` | Analyse a portfolio of stocks |
| `POST` | `/compare_stocks` | Compare two stocks |

---

## Deployment Targets

### Render

1. Create a new Web Service pointing to your repo.
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add `GEMINI_API_KEY` as an environment variable.
5. Deploy the Streamlit UI as a separate service with `streamlit run ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`.

### Railway

1. Create a new project, link your repo.
2. Add a `Procfile` with: `web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Set `GEMINI_API_KEY` in the Variables tab.

### VM (e.g. AWS EC2, DigitalOcean)

1. SSH into the VM, clone the repo.
2. Install Docker and Docker Compose.
3. Run `docker compose up -d --build`.
4. Expose ports 8000 and 8501 via firewall/security group.

---

## Logs

- Console logs: structured loguru output to stderr.
- File logs: `dump.log` in project root (10 MB rotation, 7 day retention).
- Request correlation IDs: every API response includes `X-Request-ID` header.
- Metrics: `GET /metrics` returns live counters, per-agent latencies, and error counts.
