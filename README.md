# RealDeal AI

**AI-powered real estate deal finder for U.S. investors.**

Find undervalued properties, analyze investment potential, and close smarter deals -- all from one platform.

---

## What It Does

RealDeal AI scans listings across major platforms and surfaces the best investment opportunities using AI-driven analysis.

- **Instant Deal Scoring** -- Every property gets a 0-100 investment score combining cap rate, cash flow, BRRRR potential, and neighborhood fundamentals.
- **BRRRR & Cash Flow Modeling** -- Full buy-rehab-rent-refinance-repeat analysis with customizable assumptions.
- **Market Heatmaps** -- Visualize cap rates, price growth, and population trends across 100+ U.S. metros.
- **Chrome Extension** -- Analyze any Zillow, Redfin, or Realtor.com listing in one click without leaving the page.
- **Smart Alerts** -- Get notified the moment a deal matching your criteria hits the market.
- **Deal Comparison** -- Side-by-side financials for up to 10 properties with custom overrides.
- **Property Management** -- Track tenants, leases, maintenance, and rent collection for properties you own.

---

## Screenshots

> _Screenshots will be added after the UI is finalized._

| Dashboard | Deal Browser |
|-----------|-------------|
| _coming soon_ | _coming soon_ |

| Market Heatmap | Deal Detail |
|---------------|-------------|
| _coming soon_ | _coming soon_ |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | Python 3.12, FastAPI, Pydantic v2 |
| **Database** | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2.0) |
| **Migrations** | Alembic |
| **Task Queue** | Celery + Redis |
| **AI/LLM** | Anthropic Claude, OpenAI GPT-4o |
| **Frontend** | Next.js / React, TypeScript, Tailwind CSS |
| **Maps** | Mapbox GL |
| **Chrome Extension** | Manifest V3, vanilla JS |
| **Payments** | Stripe (subscriptions), Plaid (ACH) |
| **Auth** | JWT (HS256) with bcrypt password hashing |
| **Infrastructure** | Docker Compose, Nginx, GitHub Actions CI/CD |
| **Monitoring** | Sentry (error tracking) |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/realdeal-ai.git
cd realdeal-ai
```

### 2. Set up environment variables

```bash
cp infra/.env.example .env
# Edit .env and fill in your API keys (OpenAI, Stripe, Mapbox, etc.)
```

### 3. Install dependencies

```bash
make setup
```

### 4. Start the stack

**Option A: Docker (recommended)**

```bash
make dev
```

This starts PostgreSQL, Redis, the FastAPI backend, Celery worker, and the frontend.

**Option B: Manual**

```bash
# Terminal 1 — Backend
make backend

# Terminal 2 — Frontend
make frontend

# Terminal 3 — Celery worker
make worker

# Terminal 4 — Celery beat (scheduled tasks)
make beat
```

### 5. Seed demo data

```bash
make seed
```

This creates demo accounts, 50 properties across 10 cities, market data, saved deals, and alerts.

Demo accounts (password: `demo1234`):

| Email | Plan |
|-------|------|
| `demo@realdeal.ai` | Starter (free) |
| `pro@realdeal.ai` | Growth |
| `proplus@realdeal.ai` | Pro |

### 6. Open the app

Visit [http://localhost:3000](http://localhost:3000)

API docs: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger) or [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

---

## Architecture

RealDeal AI follows a modular monolith architecture with clear separation between the API layer, business logic services, AI modules, and background task processing.

```
Browser / Extension
       |
   Nginx (reverse proxy)
       |
   ┌───┴───┐
   │FastAPI │──── Celery Workers ──── Redis (broker)
   │  API   │          |
   └───┬───┘     Scrapers / AI
       |
   PostgreSQL
```

For a full architecture deep-dive, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Project Structure

```
realdeal-ai/
├── backend/
│   ├── app/
│   │   ├── ai/                 # AI modules (deal analyzer, market analyzer, etc.)
│   │   ├── api/v1/             # FastAPI route handlers
│   │   ├── core/               # Config, database, security
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── scrapers/           # Zillow, Redfin, Realtor scrapers
│   │   ├── services/           # Business logic (verdict, neighborhood, cache)
│   │   ├── tasks/              # Celery background tasks
│   │   ├── utils/              # Shared utilities (geo, etc.)
│   │   ├── main.py             # FastAPI app entry point
│   │   └── worker.py           # Celery worker entry point
│   ├── migrations/             # Alembic database migrations
│   ├── scripts/                # Seed data, DB reset, API doc generation
│   ├── tests/                  # Backend test suite
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/                   # Next.js / React frontend
├── extension/                  # Chrome extension (Manifest V3)
├── infra/                      # Dockerfiles, nginx config, env example
├── docs/                       # Architecture, API, deployment docs
├── docker-compose.yml
├── Makefile                    # Development commands (make help)
└── README.md
```

---

## API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: Generate with `make docs` (writes to `docs/openapi.json`)

For endpoint details and usage examples, see [`docs/API.md`](docs/API.md).

---

## Running Tests

```bash
# All tests
make test

# Backend only (with coverage report)
make test-backend

# Frontend only
make test-frontend
```

Backend tests use pytest with async support. Coverage reports are generated in `backend/htmlcov/`.

---

## Deployment

The project ships with Docker Compose for local development and is designed for container-based deployment.

```bash
# Build production images
make build

# Deploy to staging
make deploy-staging
```

CI/CD is handled via GitHub Actions. See `.github/workflows/` for pipeline definitions and `docs/DEPLOYMENT.md` for full deployment instructions.

---

## Contributing

1. **Branch naming**: `feature/description`, `fix/description`, `chore/description`
2. **Commits**: Use conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`)
3. **Pull requests**: Fill out the PR template. All PRs require at least one review.
4. **Code style**:
   - Backend: Ruff for linting/formatting, mypy for type checking
   - Frontend: ESLint + Prettier
   - Run `make lint` before pushing
5. **Tests**: All new features must include tests. Maintain >80% backend coverage.

---

## Team

> _Team section -- add founders and contributors here._

---

## License

Copyright (c) 2026 RealDeal AI. All Rights Reserved.

This software is proprietary. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.
