.PHONY: install dev test lint format type-check quality clean docker-build docker-up docker-down

# ---- Setup ----
install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

venv:
	python -m venv venv
	@echo "Activate with: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)"

# ---- Run ----
dev-api:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dev-ui:
	streamlit run ui/streamlit_app.py

# ---- Quality ----
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html

lint:
	ruff check .

format:
	ruff format .

type-check:
	mypy agents/ backend/ data_sources/ langgraph/ utils/ --ignore-missing-imports

quality: lint type-check test

# ---- Docker ----
docker-build:
	docker build -t market-analyst-ai .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# ---- Cleanup ----
clean:
	rm -rf __pycache__ .pytest_cache htmlcov .coverage *.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
