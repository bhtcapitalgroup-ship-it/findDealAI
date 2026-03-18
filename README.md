# RealDeal AI

**AI-powered property management platform for small landlords (5–50 units).**

Automate 80% of your landlord work — tenant communication, maintenance coordination, rent collection, and financial tracking — all powered by AI.

---

## What It Does

RealDeal AI replaces the need for a property manager by automating daily operations with AI agents.

- **AI Tenant Communication** — Tenants text or chat with an AI that handles maintenance requests, payment questions, and lease inquiries 24/7. Escalates to you when needed.
- **Smart Maintenance** — AI diagnoses issues from photos (leak, mold, HVAC), assigns urgency, matches contractors, gets quotes, and schedules repairs.
- **Rent Collection** — Automated reminders, Stripe/ACH/Zelle payments, late fee tracking, and aging reports.
- **Financial Dashboard** — Portfolio-level view of income, expenses, NOI, cash flow, and cap rate across all properties.
- **AI Lease Analyzer** — Upload a lease PDF and get an instant breakdown of key terms, risks, and missing clauses.
- **Document Management** — Store and organize leases, inspections, contracts, and receipts with auto-tagging.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Pydantic v2 |
| **Database** | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2.0) |
| **Task Queue** | Celery + Redis |
| **AI** | Anthropic Claude (Haiku for classification, Sonnet for chat + vision, Opus for lease analysis) |
| **Frontend** | React 19, TypeScript, Tailwind CSS v4, Recharts |
| **Payments** | Stripe (cards), Plaid (ACH), Zelle (manual) |
| **SMS** | Twilio |
| **Storage** | AWS S3 |
| **Auth** | JWT (HS256) + bcrypt |
| **Infrastructure** | Docker Compose, PostgreSQL, Redis |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+

### 1. Clone the repository

```bash
git clone https://github.com/bhtcapitalgroup-ship-it/-RealDealAI.git
cd -RealDealAI
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key (required for AI features)
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### 4. Start the backend (optional — frontend works standalone with demo data)

```bash
cd backend
pip install -r requirements.txt

# Seed demo data
python seed_demo.py

# Start API server
DATABASE_URL="sqlite+aiosqlite:///./realdeal_dev.db" JWT_SECRET="dev-secret" uvicorn app.main:app --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Start with Docker (full stack)

```bash
cp .env.example .env
docker compose up
```

This starts PostgreSQL, Redis, the FastAPI backend, Celery workers, and the React frontend.

### Demo Login

```
Email:    jordan@mitchell.com
Password: demo123
```

Or use any email/password — the frontend runs in demo mode with mock data.

---

## Project Structure

```
realdeal-ai/
├── backend/
│   ├── app/
│   │   ├── ai/                 # AI modules (tenant bot, vision, lease analyzer)
│   │   ├── api/v1/             # 50 REST endpoints
│   │   ├── core/               # Config, database, security, auth
│   │   ├── models/             # 14 SQLAlchemy models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Payment, maintenance, document services
│   │   ├── tasks/              # Celery workers (reminders, contractor outreach)
│   │   ├── main.py             # FastAPI entry point
│   │   └── worker.py           # Celery worker entry point
│   ├── seed_demo.py            # Demo data seeder
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # Layout, StatCard, Badge, Modal, DataTable
│   │   ├── pages/              # 12 pages (Dashboard, Properties, Tenants, etc.)
│   │   ├── lib/                # API client, auth context, utilities
│   │   ├── App.tsx             # Route definitions
│   │   └── main.tsx            # Entry point
│   ├── Dockerfile
│   └── package.json
├── docs/                       # Product spec, architecture, roadmap, pricing
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Core Modules

### 1. Tenant Communication AI

Tenants text or chat → AI classifies intent (maintenance / payment / lease) → responds automatically → escalates if confidence < 70% or legal keywords detected.

- **Claude Haiku** for intent classification (~$0.003/message)
- **Claude Sonnet** for response generation
- Fair Housing guard rails built in

### 2. Maintenance Automation

```
Tenant reports issue → AI categorizes + assigns urgency → Matches contractor
→ Sends RFQ → Landlord approves quote → Contractor scheduled → Tenant notified
```

### 3. Vision Diagnostics

Tenant uploads a photo → Claude Sonnet Vision detects:
- Water damage, mold, structural cracks, HVAC issues, pest evidence
- Assigns severity (1-5), urgency, estimated cost range
- Auto-creates maintenance ticket

### 4. Financial Dashboard

Real-time portfolio view:
- Income vs expenses by property and category
- NOI, cash flow, cap rate, equity tracking
- P&L table, expense breakdown, collection rate
- Tax-ready CSV export

### 5. Lease Analyzer

Upload lease PDF → Claude Opus extracts:
- All key terms (rent, deposit, fees, dates, policies)
- Risk flags (unusual clauses, missing protections)
- Risk score 0-100

---

## API Endpoints (50 total)

| Group | Endpoints | Description |
|-------|-----------|-------------|
| Auth | 2 | Register, login (JWT) |
| Properties | 6 | CRUD + financials |
| Units | 4 | CRUD per property |
| Tenants | 5 | CRUD + payment history |
| Leases | 4 | CRUD with auto unit status |
| Payments | 5 | CRUD + summary + aging report |
| Maintenance | 7 | CRUD + AI diagnose + approve + complete |
| Contractors | 4 | CRUD with soft delete |
| Documents | 5 | Upload + analyze |
| AI Chat | 4 | Chat + conversations + escalations |
| Financials | 4 | Dashboard + income + expenses |
| Webhooks | 2 | Twilio SMS + Stripe |

---

## Database Schema

14 tables: `users`, `properties`, `units`, `tenants`, `leases`, `payments`, `maintenance_requests`, `maintenance_photos`, `contractors`, `quotes`, `conversations`, `messages`, `documents`, `expenses`, `notifications`

All tables use UUID primary keys, TIMESTAMPTZ timestamps, and are scoped by `landlord_id` for multi-tenancy.

---

## Pricing Model

| Tier | Price | Units | Features |
|------|-------|-------|----------|
| Starter | Free | ≤ 5 | Rent collection, basic dashboard, document storage |
| Growth | $2/unit/mo | 6–25 | + AI chat, auto reminders, maintenance AI |
| Pro | $4/unit/mo | 26–100 | + Vision diagnostics, lease analyzer, financial reports |
| Enterprise | Custom | 100+ | + API access, white-label, dedicated support |

---

## License

Copyright (c) 2026 RealDeal AI. All Rights Reserved.

This software is proprietary. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.
