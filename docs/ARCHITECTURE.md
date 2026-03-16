# RealDeal AI — System Architecture

## System Overview

```
                                    +-----------+
                                    |   CDN     |
                                    | CloudFront|
                                    +-----+-----+
                                          |
                                          v
+------------------+              +-------+--------+
|                  |   HTTPS      |                 |
|   Web Browser    +------------->+     Nginx       |
|   (Next.js SPA)  |              |  Reverse Proxy  |
|                  |<-------------+                 |
+------------------+              +---+--------+----+
                                      |        |
                           /api/*     |        |  /*
                                      v        v
                              +-------+--+  +--+--------+
                              |          |  |           |
                              | FastAPI  |  | Next.js   |
                              | Backend  |  | Frontend  |
                              | :8000    |  | :3000     |
                              +--+--+----+  +-----------+
                                 |  |
                    +------------+  +------------+
                    |                             |
                    v                             v
            +------+------+              +-------+------+
            |             |              |              |
            | PostgreSQL  |              |    Redis     |
            | + PostGIS   |              |   (Cache +   |
            | :5432       |              |    Broker)   |
            |             |              |   :6379      |
            +------+------+              +------+-------+
                   ^                            |
                   |                            v
                   |                    +-------+-------+
                   |                    |               |
                   +--------------------+ Celery Workers|
                         results        | (scraping,    |
                                        |  analysis,    |
                                        |  alerts)      |
                                        +---+---+---+---+
                                            |   |   |
                              +-------------+   |   +-------------+
                              |                 |                 |
                              v                 v                 v
                      +-------+----+    +-------+-----+   +------+------+
                      |  Proxy     |    |   AI/LLM    |   |  SendGrid   |
                      |  Layer     |    |   APIs      |   |  (Email)    |
                      | BrightData |    | OpenAI /    |   +-------------+
                      +------+-----+    | Anthropic   |
                             |          +-------------+
                             v
                    +--------+--------+
                    | Target Websites |
                    | Zillow, Redfin, |
                    | Realtor, etc.   |
                    +-----------------+
```

## Component Descriptions

### Frontend (Next.js 14)

The user-facing single-page application built with Next.js 14 using the App Router.

| Aspect | Detail |
|--------|--------|
| Framework | Next.js 14 with App Router |
| Language | TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand for client state, TanStack Query for server state |
| Maps | Mapbox GL JS for property maps and heat maps |
| Charts | Recharts for financial visualizations |
| Auth | NextAuth.js with JWT tokens |
| Rendering | SSR for SEO pages, CSR for dashboard |

Key pages:
- `/` — Landing page with market stats and CTA
- `/dashboard` — Personalized deal feed, saved properties, alerts
- `/properties` — Searchable/filterable property browser with map view
- `/properties/[id]` — Detailed property analysis with AI insights
- `/markets` — Market data explorer with comparisons
- `/alerts` — Alert management
- `/settings` — Account, billing, preferences

### API Layer (FastAPI)

High-performance async Python API serving all data to the frontend and handling authentication, authorization, and business logic.

| Aspect | Detail |
|--------|--------|
| Framework | FastAPI 0.110+ |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic v2 |
| Auth | JWT (access + refresh tokens), OAuth2 (Google) |
| Docs | Auto-generated OpenAPI/Swagger |
| Migrations | Alembic (async) |
| Rate Limiting | slowapi + Redis backend |
| Caching | Redis with configurable TTL per endpoint |

Route structure:
- `/api/v1/auth/*` — Registration, login, token refresh, password reset
- `/api/v1/properties/*` — CRUD, search, filters, nearby
- `/api/v1/deals/*` — Saved deals, comparisons, export
- `/api/v1/alerts/*` — Alert CRUD, test triggers
- `/api/v1/markets/*` — Market data, trends, comparisons
- `/api/v1/users/*` — Profile, preferences, billing
- `/ws/alerts` — WebSocket for real-time deal notifications

### Workers (Celery)

Background task processing for all compute-intensive and I/O-bound operations.

| Queue | Purpose | Concurrency |
|-------|---------|-------------|
| `default` | General tasks, data cleanup | 4 |
| `scraping` | Web scraping with proxy rotation | 8 |
| `analysis` | AI scoring, financial modeling | 4 |
| `alerts` | Email/push notifications | 2 |

Key tasks:
- `scrape_source` — Scrape listings from a specific source/region
- `enrich_property` — Add estimated rent, market comps, neighborhood data
- `analyze_property` — Run AI analysis and generate investment score
- `evaluate_alerts` — Check new properties against user alert criteria
- `send_alert_notification` — Dispatch via email, SMS, push, or webhook
- `generate_market_report` — Compile weekly market data snapshots
- `cleanup_stale_listings` — Archive sold/withdrawn properties

### Celery Beat (Scheduler)

Periodic task scheduler driving the data pipeline on a recurring basis.

| Schedule | Task | Description |
|----------|------|-------------|
| Every 6 hours | `scrape_all_sources` | Full scrape cycle across all sources |
| Every hour | `scrape_hot_markets` | Priority scrape for high-activity ZIP codes |
| Every 30 minutes | `evaluate_instant_alerts` | Check new listings against instant alerts |
| Daily 6:00 AM | `send_daily_digests` | Daily alert digests |
| Weekly Monday 8:00 AM | `send_weekly_digests` | Weekly alert digests |
| Weekly Sunday | `generate_market_reports` | Compile weekly market snapshots |
| Daily 2:00 AM | `cleanup_stale_listings` | Archive old listings, purge cache |

### Scraping Engine

Distributed scraping system that collects property listings from multiple sources.

- **Scheduler**: Celery Beat triggers scrape jobs based on priority and freshness
- **Task Queue**: Redis-backed Celery queues distribute work across workers
- **Worker Pool**: Configurable concurrency with per-source rate limiting
- **Proxy Layer**: BrightData residential proxy rotation to avoid IP blocks
- **Parsers**: Per-source HTML/API parsers with CSS selector and JSON extraction
- **Normalizer**: Standardizes data into a common schema across all sources

### AI Analysis Engine

Combines rule-based financial analysis with LLM-powered insights.

**Rule-based calculations:**
- Cap rate: `(NOI / Purchase Price) * 100`
- Cash-on-cash return: `(Annual Cash Flow / Total Cash Invested) * 100`
- Gross yield: `(Annual Rent / Purchase Price) * 100`
- Rent-to-price ratio: `Monthly Rent / Purchase Price`
- Price per sqft vs. market median

**LLM-powered analysis:**
- Natural language property summary
- Neighborhood quality assessment
- Investment thesis generation
- Risk factor identification
- Comparable property analysis narrative

**Composite Investment Score (0-100):**

| Factor | Weight | Source |
|--------|--------|--------|
| Cap rate vs. market | 20% | Calculated |
| Cash-on-cash return | 15% | Calculated |
| Price vs. estimated value | 15% | Calculated |
| Market trend (appreciation) | 15% | Market data |
| Rent growth potential | 10% | Market data |
| Days on market | 10% | Listing data |
| Neighborhood quality | 10% | AI assessment |
| Data completeness | 5% | Internal |

### Database (PostgreSQL 16 + PostGIS)

Primary data store with geospatial capabilities.

- **PostGIS**: Enables `ST_DWithin`, `ST_Distance` for radius searches and proximity queries
- **JSONB columns**: Flexible storage for AI analysis results, raw scraped data, alert criteria
- **UUID primary keys**: Globally unique, safe for distributed inserts
- **Trigger-based `updated_at`**: Automatic timestamp maintenance
- **Connection pooling**: asyncpg with SQLAlchemy async engine

### Cache Layer (Redis 7)

Multi-purpose Redis instance serving three roles:

1. **Application Cache**: Property search results, market data, user sessions (TTL: 5-60 minutes)
2. **Celery Broker**: Task queue message transport
3. **Rate Limiting**: Per-user and per-IP request counters with sliding window

### Message Queue (Redis / Celery)

Redis serves as the Celery message broker, supporting:
- Priority queues (scraping > analysis > alerts > default)
- Task result storage with TTL
- Task retry with exponential backoff
- Dead letter queue for failed tasks

## Data Flow

```
1. DISCOVERY         2. SCRAPING          3. NORMALIZATION
+------------+       +------------+       +---------------+
| Celery Beat| ----> | Celery     | ----> | Data Pipeline |
| schedules  |       | Workers    |       | - Clean HTML  |
| scrape jobs|       | + Proxies  |       | - Extract     |
+------------+       +------------+       | - Standardize |
                                          +-------+-------+
                                                  |
4. DEDUPLICATION     5. ENRICHMENT        6. AI ANALYSIS
+---------------+    +---------------+    +---------------+
| Address match | <--+ Add rent est. | <--+ LLM summary   |
| MLS number    |    | Market comps  |    | Score calc    |
| Fuzzy match   |    | Neighborhood  |    | Risk assess   |
+-------+-------+    +---------------+    +-------+-------+
        |                                         |
7. STORAGE           8. ALERTING          9. DELIVERY
+---------------+    +---------------+    +---------------+
| PostgreSQL    | -->| Match against | -->| Email         |
| Update/Insert |    | user criteria |    | Push          |
| Invalidate    |    | JSONB query   |    | WebSocket     |
| cache         |    +---------------+    | Webhook       |
+---------------+                         +---------------+
```

### Step-by-Step

1. **Discovery**: Celery Beat fires scheduled scrape tasks targeting specific sources and geographies. High-activity ZIP codes are scraped more frequently.

2. **Scraping**: Workers pull tasks from the `scraping` queue. Each task configures the appropriate parser, selects a proxy from the BrightData pool, and fetches listing pages. Failed requests are retried with exponential backoff and proxy rotation.

3. **Normalization**: Raw HTML/JSON responses are parsed into a standardized `PropertyData` schema. Address components are extracted and standardized. Prices, dates, and measurements are normalized.

4. **Deduplication**: Before insertion, the pipeline checks for existing records via MLS number (exact match) and address similarity (trigram index, threshold 0.85). Duplicates trigger an update rather than insert.

5. **Enrichment**: Properties are enriched with estimated rent (from Rentometer data or comparable analysis), market statistics for the ZIP code, school ratings, and walkability scores.

6. **AI Analysis**: The analysis engine computes financial metrics (cap rate, cash-on-cash, yield) and sends property data to the LLM for a natural language summary and risk assessment. The composite investment score is calculated from weighted factors.

7. **Storage**: Enriched, analyzed properties are upserted into PostgreSQL. Redis cache keys for affected search queries and ZIP codes are invalidated.

8. **Alerting**: New and updated properties are evaluated against all active alert criteria using JSONB containment queries. Matching alerts are queued for delivery.

9. **Delivery**: Alert notifications are sent through the user's preferred channel (email via SendGrid, push notification, WebSocket for connected clients, or webhook for integrations).

## Technology Choices and Rationale

| Technology | Chosen | Alternatives Considered | Rationale |
|-----------|--------|------------------------|-----------|
| **Backend Framework** | FastAPI | Django REST, Flask | Async-native, automatic OpenAPI docs, Pydantic validation, best performance for I/O-heavy workload |
| **Frontend Framework** | Next.js 14 | Remix, SvelteKit | Largest ecosystem, excellent SSR/SSG support, Vercel deployment option, strong hiring pool |
| **Database** | PostgreSQL 16 + PostGIS | MySQL, MongoDB | JSONB for flexible data, PostGIS for geo queries, mature ecosystem, excellent performance |
| **Cache / Broker** | Redis 7 | RabbitMQ, Memcached | Single service for cache + broker + rate limiting, simple ops, excellent performance |
| **Task Queue** | Celery | Dramatiq, Huey, arq | Most mature Python task queue, good monitoring (Flower), extensive documentation |
| **ORM** | SQLAlchemy 2.0 (async) | Tortoise, SQLModel | Most feature-rich Python ORM, excellent async support in v2, wide community |
| **Proxy Service** | BrightData | ScraperAPI, Oxylabs | Largest residential proxy pool, reliable, good API |
| **AI/LLM** | OpenAI GPT-4o / Claude | Llama, Mistral | Best quality for structured analysis, fast, reliable API |
| **Email** | SendGrid | AWS SES, Postmark | Easy setup, good deliverability, reasonable pricing |
| **Maps** | Mapbox GL JS | Google Maps, Leaflet | Better customization, performance with large datasets, competitive pricing |
| **Payments** | Stripe | Paddle, LemonSqueezy | Industry standard, excellent API, subscription management |

## Scaling Strategy

### Phase 1: MVP (0-1,000 users)

- Single docker-compose deployment on a beefy VPS (8 CPU, 32 GB RAM)
- Single PostgreSQL instance, single Redis instance
- 4 Celery workers

### Phase 2: Growth (1,000-10,000 users)

- **Compute**: Migrate to Kubernetes (EKS/GKE) or managed containers (Cloud Run / ECS)
- **Database**: Managed PostgreSQL (RDS/Cloud SQL) with read replicas for search queries
- **Cache**: Managed Redis (ElastiCache / Memorystore) with cluster mode
- **Workers**: Horizontal scaling — auto-scale Celery workers based on queue depth
- **CDN**: CloudFront/Fastly for static assets and API response caching
- **Search**: Consider Elasticsearch/Meilisearch for property full-text search

### Phase 3: Scale (10,000+ users)

- **Database**: Partitioning `properties` table by state, time-series partitioning for `market_data`
- **Caching**: Multi-layer cache (L1 in-process, L2 Redis, L3 CDN)
- **Workers**: Dedicated worker pools per queue with independent autoscaling
- **API**: Multiple backend replicas behind ALB with connection draining
- **Async**: Event-driven architecture with SNS/SQS or Kafka for inter-service communication
- **Read optimization**: Materialized views for common aggregations and leaderboards

### Database Scaling Specifics

```
Phase 2:
  Primary (write) ──> Read Replica 1 (API search queries)
                  ──> Read Replica 2 (analytics/reports)

Phase 3:
  Primary (write) ──> Replica 1 (API reads - West)
                  ──> Replica 2 (API reads - East)
                  ──> Replica 3 (Analytics)
  + PgBouncer connection pooling
  + Table partitioning by state (properties) and month (market_data)
```

## Security Considerations

### Authentication and Authorization
- JWT tokens with short-lived access tokens (30 min) and longer refresh tokens (7 days)
- Refresh token rotation — each use issues a new refresh token and invalidates the old one
- Role-based access control (free, starter, pro, enterprise, admin)
- Rate limiting per tier (see API documentation)

### Scraping Security
- **Proxy rotation**: BrightData residential proxies, rotate per-request
- **Request throttling**: Configurable delay between requests per source (2-10 seconds)
- **Browser fingerprint randomization**: Random user agents, accept-language headers, viewport sizes
- **Distributed scheduling**: Randomized timing to avoid pattern detection
- **Respectful scraping**: Honor robots.txt where possible, avoid excessive load

### Data Security
- **Encryption at rest**: PostgreSQL with encrypted storage (AWS RDS encryption / GCP encryption)
- **Encryption in transit**: TLS 1.2+ for all connections (API, database, Redis, external APIs)
- **Secrets management**: Environment variables, never committed to source control. Production: AWS Secrets Manager or HashiCorp Vault
- **PII handling**: User emails and passwords (bcrypt hashed) are the only PII stored. No credit card data (handled by Stripe)
- **SQL injection prevention**: SQLAlchemy parameterized queries, Pydantic input validation
- **XSS/CSRF**: Next.js built-in protections, CORS configuration, SameSite cookies
- **Dependency scanning**: Dependabot / Snyk for vulnerability detection
- **Audit logging**: All admin actions and data exports are logged

### Infrastructure Security
- **Network isolation**: Private subnets for database and Redis, public subnet only for load balancer
- **Least privilege**: IAM roles with minimal permissions per service
- **Container security**: Non-root users in Docker, read-only filesystems where possible
- **Monitoring**: Sentry for error tracking, CloudWatch/Datadog for metrics, PagerDuty for alerts
