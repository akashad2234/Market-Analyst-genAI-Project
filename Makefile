.PHONY: install dev test lint format type-check quality clean docker-build docker-up docker-down \
       react-install react-dev react-build react-test react-lint dev-all test-all

# ---- Setup ----
install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

react-install:
	cd react-ui && npm install

install-all: install react-install

venv:
	python -m venv venv
	@echo "Activate with: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)"

# ---- Run ----
dev-api:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --timeout-keep-alive 120

dev-ui:
	streamlit run ui/streamlit_app.py

dev-ui-standalone:
	streamlit run streamlit_app.py

react-dev:
	cd react-ui && npm run dev

dev-all:
	@echo "Start API and React UI in separate terminals:"
	@echo "  make dev-api"
	@echo "  make react-dev"

# ---- Quality ----
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html

react-test:
	cd react-ui && npm test

test-all: test react-test

lint:
	ruff check .

react-lint:
	cd react-ui && npm run lint

format:
	ruff format .

type-check:
	mypy agents/ backend/ data_sources/ langgraph/ utils/ --ignore-missing-imports

quality: lint type-check test react-test

# ---- Build ----
react-build:
	cd react-ui && npm run build

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
	rm -rf react-ui/dist react-ui/node_modules/.cache
