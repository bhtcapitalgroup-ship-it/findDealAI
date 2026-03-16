# RealDeal AI — 8-Week MVP Roadmap

## Team

| Role | Count | Allocation |
|------|-------|------------|
| Backend Engineer | 2 | Full-time |
| Frontend Engineer | 1 | Full-time |
| AI/ML Engineer | 1 | Full-time |

**Total**: 4 engineers, 8 weeks = 32 person-weeks

---

## Week 1-2: Foundation

**Theme**: Infrastructure, auth, data models, and first scraper proof-of-concept.

### Week 1

| Task | Owner | Est. |
|------|-------|------|
| Set up monorepo structure (backend, frontend, infra, docs) | BE-1 | 0.5d |
| Docker Compose with PostgreSQL + PostGIS, Redis | BE-1 | 0.5d |
| Alembic migrations: all 5 tables with indexes and triggers | BE-1 | 1d |
| FastAPI project scaffold: routers, middleware, error handling | BE-2 | 1d |
| Auth system: registration, login, JWT access/refresh tokens | BE-2 | 2d |
| Password reset flow + email verification (SendGrid) | BE-2 | 1d |
| Next.js 14 project setup: App Router, Tailwind, shadcn/ui | FE | 2d |
| Auth pages: login, register, forgot password | FE | 2d |
| Research target site structures, select initial parsing strategy | AI/ML | 2d |
| Build scraper framework: base class, proxy integration, retry logic | AI/ML | 2d |

### Week 2

| Task | Owner | Est. |
|------|-------|------|
| Properties CRUD API: create, read, list with basic filters | BE-1 | 2d |
| Search API: pagination, sorting, price/location/type filters | BE-1 | 2d |
| User profile API, subscription tier middleware | BE-2 | 1d |
| Rate limiting with slowapi + Redis | BE-2 | 1d |
| Celery setup: broker config, worker, beat scheduler | BE-2 | 1d |
| API client layer (Axios/fetch wrapper, auth interceptor) | FE | 1d |
| Layout shell: sidebar nav, header, responsive scaffold | FE | 2d |
| Basic property list page with table view | FE | 2d |
| First scraper: Zillow listing parser | AI/ML | 3d |
| Data normalization pipeline: address standardization | AI/ML | 1d |

### Milestone 1 (End of Week 2)
- [x] Users can register, login, and browse basic property data
- [x] One scraper (Zillow) producing real data into the database
- [x] Infrastructure running in Docker with automated migrations
- [x] CI pipeline: lint, type check, unit tests

---

## Week 3-4: Core Scrapers + AI Analysis

**Theme**: Expand data sources, build the AI scoring engine, add geospatial search.

### Week 3

| Task | Owner | Est. |
|------|-------|------|
| Geospatial search: PostGIS radius queries, lat/lng endpoint | BE-1 | 2d |
| Advanced filters: bedrooms, sqft, year_built, score ranges | BE-1 | 1d |
| Property detail endpoint with full data | BE-1 | 1d |
| Deduplication pipeline: MLS match + address fuzzy match | BE-2 | 2d |
| Scrape scheduling: Celery Beat config, priority queues | BE-2 | 1d |
| Monitoring: Flower dashboard, task failure alerting | BE-2 | 1d |
| Property detail page: photos, details, location map | FE | 3d |
| Search filters UI: dropdowns, sliders, tag inputs | FE | 2d |
| Second scraper: Redfin | AI/ML | 2d |
| Third scraper: Realtor.com | AI/ML | 2d |

### Week 4

| Task | Owner | Est. |
|------|-------|------|
| Financial calculations engine: cap rate, CoC, yield, PPSF | BE-1 | 2d |
| Market data table + API: ingest, query, trends | BE-1 | 2d |
| Enrichment pipeline: rent estimation, tax lookup | BE-2 | 2d |
| Property update pipeline: detect changes, re-score | BE-2 | 2d |
| Property card component with score badge and key metrics | FE | 1d |
| Map integration: Mapbox GL, property pins, clustering | FE | 3d |
| Investment scoring algorithm: weighted composite score | AI/ML | 2d |
| LLM integration: property summary + risk assessment | AI/ML | 2d |

### Milestone 2 (End of Week 4)
- [x] 3 scrapers running on schedule producing 5K+ listings
- [x] AI investment scores and summaries on all properties
- [x] Geospatial search working with map view
- [x] Financial metrics calculated for all properties with rent data
- [x] Deduplication preventing duplicate listings

---

## Week 5-6: Frontend Dashboard + Deal Browser + Maps

**Theme**: Build the full user-facing experience.

### Week 5

| Task | Owner | Est. |
|------|-------|------|
| Saved deals API: CRUD, labels, favorites, notes | BE-1 | 2d |
| Deal comparison API: side-by-side with AI recommendation | BE-1 | 1d |
| Export API: CSV and PDF generation | BE-1 | 1d |
| Alerts API: CRUD, criteria validation, test trigger | BE-2 | 2d |
| Alert matching engine: JSONB query against new properties | BE-2 | 2d |
| Dashboard page: personalized feed, stats, recent deals | FE | 3d |
| Saved deals page: list, filter, favorites, notes editor | FE | 2d |
| Rentometer data integration | AI/ML | 1d |
| Public records scraper (county assessor data) | AI/ML | 2d |
| Improve scoring model with market data integration | AI/ML | 1d |

### Week 6

| Task | Owner | Est. |
|------|-------|------|
| Financial projections endpoint (year 1, 5, 10 cash flow) | BE-1 | 2d |
| WebSocket: real-time alert delivery | BE-1 | 1d |
| Email alert templates: new deal, daily digest, weekly digest | BE-2 | 2d |
| Celery Beat scheduled alert digests (daily/weekly) | BE-2 | 1d |
| Stripe integration: checkout, webhook, tier management | BE-2 | 2d |
| Property detail page: AI analysis section, financials tab | FE | 2d |
| Comparison view: side-by-side cards with charts | FE | 2d |
| Market data page: ZIP code lookup, trend charts | FE | 2d |
| AI market insights generation (per-ZIP weekly) | AI/ML | 2d |
| Comparable property matching algorithm | AI/ML | 2d |

### Milestone 3 (End of Week 6)
- [x] Full deal management: save, compare, export, notes
- [x] Alert system: create criteria, receive email notifications
- [x] Financial projections with customizable assumptions
- [x] Market data explorer with trend visualizations
- [x] Stripe payments working for tier upgrades
- [x] 5 data sources feeding the pipeline

---

## Week 7: Alerts, Comparisons, Export, Subscriptions

**Theme**: Polish features, add remaining subscription functionality, harden the system.

| Task | Owner | Est. |
|------|-------|------|
| Subscription management API: upgrade, downgrade, cancel | BE-1 | 1d |
| Usage tracking: deal limits, API rate limits per tier | BE-1 | 1d |
| Admin API: user management, scraper status, system health | BE-1 | 2d |
| Alert optimization: batch processing, delivery dedup | BE-2 | 1d |
| Retry and dead-letter queue handling | BE-2 | 1d |
| Data quality scoring and flagging | BE-2 | 1d |
| Nginx configuration: SSL, rate limiting, WebSocket proxy | BE-2 | 1d |
| Alert management page: create/edit wizard, channel selection | FE | 2d |
| Settings page: profile, password, subscription, billing | FE | 2d |
| Pricing page with tier comparison | FE | 1d |
| Optimize scoring: A/B test weights, validate against sold data | AI/ML | 2d |
| Neighborhood quality scoring | AI/ML | 1d |
| Scraper resilience: handle site changes, parser fallbacks | AI/ML | 1d |

### Milestone 4 (End of Week 7)
- [x] Full subscription lifecycle working (upgrade/downgrade/cancel)
- [x] Tier-based feature gating enforced across all endpoints
- [x] Alert delivery optimized and deduplicated
- [x] Admin dashboard for operational monitoring
- [x] All major user-facing pages complete

---

## Week 8: Polish, Testing, Soft Launch

**Theme**: Quality, performance, security, and initial users.

| Task | Owner | Est. |
|------|-------|------|
| Load testing: k6 scripts, identify bottlenecks | BE-1 | 1d |
| Query optimization: EXPLAIN ANALYZE on slow queries, add missing indexes | BE-1 | 1d |
| Security audit: input validation, SQL injection, XSS review | BE-1 | 1d |
| API documentation: OpenAPI spec review, example cleanup | BE-1 | 1d |
| Sentry integration: error tracking, performance monitoring | BE-2 | 0.5d |
| Production deployment: managed DB, Redis, container orchestration | BE-2 | 1.5d |
| Backup and recovery testing | BE-2 | 0.5d |
| Monitoring dashboards: Grafana/Datadog, PagerDuty alerts | BE-2 | 1d |
| Responsive design polish, mobile testing | FE | 1d |
| Performance: Lighthouse audit, code splitting, image optimization | FE | 1d |
| Landing page with product demo video embed | FE | 1d |
| SEO: meta tags, structured data, sitemap | FE | 1d |
| End-to-end testing: critical user flows | AI/ML | 1d |
| Scoring validation: manual review of top/bottom scored properties | AI/ML | 1d |
| Scraper monitoring: success rates, data freshness dashboard | AI/ML | 1d |
| Beta user onboarding: invite 100 investors, feedback collection | ALL | 1d |

### Milestone 5 — MVP Launch (End of Week 8)
- [x] Production deployment on managed infrastructure
- [x] 100 beta users onboarded and providing feedback
- [x] 50K+ properties indexed with AI scores
- [x] All scrapers running on schedule with >95% success rate
- [x] Monitoring and alerting operational
- [x] <2 second page load time for property search
- [x] Zero critical security issues

---

## Post-MVP Roadmap (Weeks 9-16)

| Week | Focus | Key Deliverables |
|------|-------|-----------------|
| 9-10 | User Feedback Integration | Top 10 user-requested features, UX improvements, bug fixes |
| 11-12 | Growth Features | Referral system, public market reports (SEO), embeddable widgets |
| 13-14 | Mobile App | React Native app with push notifications |
| 15-16 | Scale & Monetize | Expand to 20 metros, A/B test pricing, affiliate partnerships |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Target site structure change breaks scraper | High | Medium | Parser versioning, automated detection of parse failures, fallback parsers |
| IP blocking despite proxy rotation | Medium | High | Multiple proxy providers, browser fingerprint randomization, request rate tuning |
| AI scoring inaccuracy (user trust) | Medium | High | Human validation of top deals, user feedback loop, transparent methodology |
| PostgreSQL performance at 1M+ properties | Low | High | Partitioning strategy planned, read replicas, query optimization sprint in week 8 |
| Stripe integration delays | Low | Medium | Start integration in week 6, use test mode for all dev |
| Scope creep | High | Medium | Strict feature freeze after week 6, defer nice-to-haves to post-MVP |
| Key team member unavailability | Low | High | Document all systems, pair programming on critical paths, no single points of failure |
| Legal challenge from scraped sites | Low | High | Legal review of ToS, comply with robots.txt, rate limit to respectful levels, consider data licensing |

---

## Definition of Done (per feature)

- [ ] Code reviewed and approved by at least 1 other engineer
- [ ] Unit tests with >80% coverage on business logic
- [ ] Integration test for API endpoints
- [ ] Documented in API.md (if API change)
- [ ] No regressions in existing tests
- [ ] Performance acceptable (<500ms API response, <2s page load)
- [ ] Error handling: graceful failures, user-friendly messages
- [ ] Logging: structured logs for debugging
