# ===========================================================================
# RealDeal AI — Development Commands
# ===========================================================================

.PHONY: help setup dev backend frontend worker beat test test-backend \
        test-frontend lint seed reset-db migrate new-migration build \
        deploy-staging clean docs

SHELL := /bin/bash
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

setup: ## Create .env from example, install backend + frontend deps
	@echo "==> Copying environment files ..."
	@test -f .env || cp infra/.env.example .env && echo "    .env created (edit before running)"
	@test -f $(BACKEND_DIR)/.env || cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env 2>/dev/null || true
	@echo "==> Installing backend dependencies ..."
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	@echo "==> Installing frontend dependencies ..."
	cd $(FRONTEND_DIR) && npm install
	@echo ""
	@echo "Setup complete! Edit .env with your API keys, then run: make dev"

# ---------------------------------------------------------------------------
# Development servers
# ---------------------------------------------------------------------------

dev: ## Start docker-compose in dev mode (Postgres, Redis, API, Frontend)
	docker compose up --build

backend: ## Run FastAPI dev server with hot reload (port 8000)
	cd $(BACKEND_DIR) && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend: ## Run Next.js / Vite dev server (port 3000)
	cd $(FRONTEND_DIR) && npm run dev

worker: ## Start Celery worker
	cd $(BACKEND_DIR) && celery -A app.worker worker --loglevel=info --concurrency=4

beat: ## Start Celery beat scheduler
	cd $(BACKEND_DIR) && celery -A app.worker beat --loglevel=info

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests with coverage
	cd $(BACKEND_DIR) && python -m pytest tests/ -v --tb=short \
		--cov=app --cov-report=term-missing --cov-report=html:htmlcov

test-frontend: ## Run frontend tests
	cd $(FRONTEND_DIR) && npm test

# ---------------------------------------------------------------------------
# Linting & formatting
# ---------------------------------------------------------------------------

lint: ## Run all linters (ruff, mypy, eslint, prettier)
	@echo "==> Backend: ruff ..."
	cd $(BACKEND_DIR) && ruff check app/ tests/ --fix
	@echo "==> Backend: mypy ..."
	cd $(BACKEND_DIR) && mypy app/ --ignore-missing-imports || true
	@echo "==> Frontend: eslint ..."
	cd $(FRONTEND_DIR) && npx eslint src/ --fix || true
	@echo "==> Frontend: prettier ..."
	cd $(FRONTEND_DIR) && npx prettier --write "src/**/*.{ts,tsx,css}" || true

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

seed: ## Populate database with demo data
	cd $(BACKEND_DIR) && python scripts/seed_data.py

reset-db: ## Drop all tables and re-run migrations (DEVELOPMENT ONLY)
	cd $(BACKEND_DIR) && python scripts/reset_db.py

migrate: ## Run Alembic migrations (upgrade to head)
	cd $(BACKEND_DIR) && alembic upgrade head

new-migration: ## Create a new Alembic migration (usage: make new-migration msg="add foo table")
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(msg)"

# ---------------------------------------------------------------------------
# Build & deploy
# ---------------------------------------------------------------------------

build: ## Build Docker images for production
	docker compose -f docker-compose.yml build

deploy-staging: ## Deploy to staging environment
	@echo "==> Building images ..."
	docker compose -f docker-compose.yml build
	@echo "==> Pushing images ..."
	docker compose -f docker-compose.yml push
	@echo "==> Deploying to staging ..."
	@echo "    (Configure your CI/CD pipeline in .github/workflows/)"
	@echo "    See docs/DEPLOYMENT.md for full instructions."

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

docs: ## Generate OpenAPI JSON documentation
	cd $(BACKEND_DIR) && python scripts/generate_api_docs.py -o ../docs/openapi.json

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Clean generated files, caches, and build artifacts
	@echo "==> Cleaning Python caches ..."
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	rm -rf $(BACKEND_DIR)/.mypy_cache 2>/dev/null || true
	@echo "==> Cleaning frontend build ..."
	rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/.next 2>/dev/null || true
	@echo "==> Cleaning Docker volumes ..."
	docker compose down -v 2>/dev/null || true
	@echo "Clean complete."
