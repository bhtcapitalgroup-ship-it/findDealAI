# RealDeal AI — MVP Roadmap

---

## Phase Overview

```
Phase 0: Foundation       ████░░░░░░░░░░░░░░░░░░░░░░░░░░  Weeks 1-4
Phase 1: Core MVP         ░░░░████████░░░░░░░░░░░░░░░░░░  Weeks 5-10
Phase 2: AI Layer         ░░░░░░░░░░░░████████░░░░░░░░░░  Weeks 11-16
Phase 3: Polish & Launch  ░░░░░░░░░░░░░░░░░░░░██████░░░░  Weeks 17-20
Phase 4: Growth           ░░░░░░░░░░░░░░░░░░░░░░░░░░████  Weeks 21-26
```

---

## Phase 0: Foundation (Weeks 1-4)

**Goal:** Scaffolding, auth, deployment pipeline.

| Task | Details | Priority |
|------|---------|----------|
| Project setup | FastAPI + React + PostgreSQL + Docker Compose | P0 |
| CI/CD | GitHub Actions → AWS ECS (staging + prod) | P0 |
| Auth system | JWT auth, landlord registration, email verification | P0 |
| Database | Schema migration setup (Alembic), seed data | P0 |
| S3 setup | File upload/download with pre-signed URLs | P0 |
| Design system | Tailwind + component library (shadcn/ui) | P0 |
| Landlord onboarding | Add property → add units → add tenants flow | P0 |

**Exit Criteria:** Landlord can sign up, add a property with units, and invite a tenant.

---

## Phase 1: Core MVP (Weeks 5-10)

**Goal:** Core property management without AI (functional baseline).

| Task | Details | Priority |
|------|---------|----------|
| Tenant portal | OTP login, view unit info, view lease | P0 |
| Rent collection | Stripe integration, manual payment recording | P0 |
| ACH setup | Plaid Link, bank account connection | P0 |
| Payment reminders | Cron-based reminder emails/SMS (Twilio) | P0 |
| Maintenance requests | CRUD, photo upload, status tracking | P0 |
| Contractor directory | Add/manage contractors, manual assignment | P1 |
| Document upload | S3 upload, tagging, property/unit association | P1 |
| Basic dashboard | Unit count, occupancy, rent collected this month | P1 |
| Notification system | In-app + email notifications | P1 |

**Exit Criteria:** Landlord can collect rent, tenants can submit maintenance requests, basic reporting works.

---

## Phase 2: AI Layer (Weeks 11-16)

**Goal:** Add AI to every workflow.

| Task | Details | Priority |
|------|---------|----------|
| TenantBot — SMS | Twilio webhook → intent classification → response | P0 |
| TenantBot — Web chat | In-app chat widget for tenant portal | P0 |
| Maintenance AI | Auto-categorize, auto-assign urgency | P0 |
| Vision diagnostics | Photo analysis for maintenance requests | P0 |
| Contractor matching | Auto-match and send RFQ to relevant contractors | P1 |
| Lease analyzer | Upload PDF → extract terms → risk flags | P1 |
| AI escalation system | Confidence thresholds, landlord review queue | P0 |
| Guard rails | Fair Housing compliance, no legal advice, PII protection | P0 |
| Smart reminders | AI-tuned reminder timing and tone | P1 |

**Exit Criteria:** Tenant can text about a leak, AI diagnoses it from photo, contacts plumber, schedules repair — landlord only approves the quote.

---

## Phase 3: Polish & Launch (Weeks 17-20)

**Goal:** Production-ready, real users.

| Task | Details | Priority |
|------|---------|----------|
| Financial dashboard | NOI, cash flow, cap rate, expense tracking | P0 |
| P&L reports | Per-property, downloadable PDF/CSV | P0 |
| Lease renewal alerts | Auto-detect expiring leases, prompt landlord | P1 |
| Zelle support | Manual confirmation flow with receipt upload | P1 |
| Mobile responsive | Full responsive design for landlord + tenant | P0 |
| Security audit | Pen test, dependency audit, OWASP check | P0 |
| Performance testing | Load test AI service, optimize cold starts | P1 |
| Beta program | 10 landlords, 50-100 units, feedback loop | P0 |
| Landing page | Marketing site with waitlist | P0 |
| Stripe Connect | Landlord payouts setup | P0 |

**Exit Criteria:** 10 beta landlords actively using the platform. <2% AI escalation rate on routine queries.

---

## Phase 4: Growth (Weeks 21-26)

**Goal:** Scale and differentiate.

| Task | Details | Priority |
|------|---------|----------|
| WhatsApp channel | Additional tenant communication channel | P1 |
| Email parsing | Inbound email → intent → workflow | P1 |
| Expense auto-categorization | AI categorize from receipts | P1 |
| Tax export | Schedule E ready export | P1 |
| Tenant screening (integration) | TransUnion/Experian API | P2 |
| Multi-language | Spanish full support | P1 |
| Native mobile app | React Native (landlord app) | P2 |
| Contractor marketplace | Open network of verified contractors | P2 |
| API for integrations | Webhooks + REST API for third-party tools | P2 |

---

## Team Composition (MVP)

| Role | Count | Responsibility |
|------|-------|---------------|
| Full-stack engineer | 2 | Core API + React frontend |
| AI/ML engineer | 1 | All AI modules, prompt engineering |
| Designer | 1 (part-time) | UX/UI, design system |
| Founder/PM | 1 | Product, beta users, business |

**Total:** 4-5 people for 6-month MVP.

---

## Key Milestones

```
Week  4:  Internal demo — "Hello World" (onboarding + auth)
Week  8:  Alpha — Collect rent from a test tenant
Week 12:  AI Demo Day — Tenant texts about leak → AI handles it end-to-end
Week 16:  Feature complete MVP
Week 18:  Beta launch (10 landlords)
Week 22:  Public launch (waitlist)
Week 26:  100 landlords target
```

---

## Technical Debt Budget

Reserve 20% of engineering time for:
- Test coverage (target: 80% on core API, 90% on payment logic)
- Monitoring + alerting (Datadog / CloudWatch)
- AI prompt iteration based on real conversations
- Database query optimization as data grows
