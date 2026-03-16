# RealDeal AI — Zillow Investment Analyzer Chrome Extension

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   CHROME EXTENSION                       │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Content   │  │ Side Panel   │  │ Background        │  │
│  │ Script    │──│ (UI)         │  │ Service Worker     │  │
│  │           │  │              │  │                    │  │
│  │ • Scrape  │  │ • Metrics    │  │ • API calls       │  │
│  │   Zillow  │  │ • Charts     │  │ • Cache mgmt      │  │
│  │ • Detect  │  │ • Verdict    │  │ • Tab detection    │  │
│  │   page    │  │ • Comps      │  │ • Rate limiting    │  │
│  └──────────┘  └──────────────┘  └─────────┬─────────┘  │
│                                             │            │
└─────────────────────────────────────────────┼────────────┘
                                              │ HTTPS
                                              ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND API (Python/FastAPI)            │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ /analyze   │  │ /rent      │  │ /neighborhood      │ │
│  │            │  │            │  │                     │ │
│  │ Investment │  │ Rent       │  │ Crime, schools,     │ │
│  │ metrics    │  │ estimation │  │ demographics        │ │
│  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘ │
│        │               │                    │            │
│        ▼               ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              LLM Analysis Layer (Claude)             │ │
│  │  • Synthesize all data into deal verdict            │ │
│  │  • Generate investment narrative                     │ │
│  │  • Risk assessment                                   │ │
│  └─────────────────────────────────────────────────────┘ │
│        │               │                    │            │
│        ▼               ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              External Data Sources                   │ │
│  │  Rentcast · Census · FBI Crime · GreatSchools        │ │
│  │  Redfin · FRED · BLS                                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐      │
│  │ Redis    │  │ Postgres │  │ Rate Limiter      │      │
│  │ Cache    │  │ History  │  │ (per-user)        │      │
│  └──────────┘  └──────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Chrome Extension Structure

```
realdeal-extension/
├── manifest.json
├── background/
│   └── service-worker.js       # Tab detection, API orchestration, caching
├── content/
│   └── scraper.js              # Extracts property data from Zillow DOM
├── sidepanel/
│   ├── panel.html              # Side panel UI shell
│   ├── panel.js                # Renders metrics, charts, verdict
│   └── panel.css               # Styling
├── shared/
│   ├── api-client.js           # Backend API wrapper
│   ├── constants.js            # Zillow selectors, API endpoints
│   └── formatters.js           # Currency, percentage formatting
├── icons/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
└── lib/
    └── chart.min.js            # Lightweight charting (Chart.js or similar)
```

### manifest.json

```json
{
  "manifest_version": 3,
  "name": "RealDeal AI",
  "version": "1.0.0",
  "description": "Real-time investment analysis for Zillow listings",
  "permissions": ["sidePanel", "activeTab", "storage"],
  "host_permissions": ["https://www.zillow.com/*"],
  "background": {
    "service_worker": "background/service-worker.js"
  },
  "content_scripts": [
    {
      "matches": ["https://www.zillow.com/homedetails/*"],
      "js": ["content/scraper.js"],
      "run_at": "document_idle"
    }
  ],
  "side_panel": {
    "default_path": "sidepanel/panel.html"
  },
  "icons": {
    "16": "icons/icon-16.png",
    "48": "icons/icon-48.png",
    "128": "icons/icon-128.png"
  }
}
```

---

## 2. Content Script — Property Scraper

The scraper extracts structured data from Zillow's DOM. Zillow uses React with
server-rendered HTML, so we target stable data attributes and semantic elements.

### Extraction Strategy

```
Target data points and where they live on the page:

Price           → [data-testid="price"] or .summary-container .ds-value
Beds/Baths      → [data-testid="bed-bath-beyond"] spans
Sqft            → .ds-bed-bath-table span (containing "sqft")
Year Built      → Facts & Features section, "Year Built" row
Address         → h1.ds-address-container or meta[property="og:title"]
Zestimate       → [data-testid="zestimate-text"]
Property Type   → Facts & Features, "Type" row
Lot Size        → Facts & Features, "Lot" row
HOA             → .ds-home-fact-list-container, "HOA" row
Tax History     → Price/Tax History table
```

### Fallback: JSON-LD / Next.js Data

Zillow embeds structured data in `<script type="application/ld+json">` and in
`__NEXT_DATA__`. If DOM scraping fails, parse these as fallback:

```javascript
// Primary: JSON-LD
const jsonLd = document.querySelector('script[type="application/ld+json"]');

// Secondary: Next.js hydration data
const nextData = document.getElementById('__NEXT_DATA__');
```

### Resilience

- Use MutationObserver to handle SPA navigation (Zillow uses client-side routing)
- Retry extraction 3x with 500ms delay if key fields are missing
- Validate extracted data (price > 0, sqft > 0, etc.) before sending

---

## 3. Backend API (Python / FastAPI)

### Endpoints

```
POST /api/v1/analyze
  Input:  { address, price, sqft, beds, baths, year_built, property_type, hoa, zestimate }
  Output: { rent_estimate, cap_rate, cash_flow, brrrr, flip, neighborhood, verdict }

GET  /api/v1/rent-estimate?address=...&beds=...&baths=...&sqft=...
  Output: { estimated_rent, confidence, comps: [...] }

GET  /api/v1/neighborhood?zip=...&lat=...&lng=...
  Output: { crime_rate, school_rating, pop_growth, rent_growth, median_income }

GET  /api/v1/health
  Output: { status: "ok" }
```

### `/analyze` — Main Orchestration Endpoint

This is the primary endpoint. It:

1. Receives scraped property data from the extension
2. Fetches rent estimate, neighborhood data, and comps in parallel
3. Calculates investment metrics
4. Sends everything to Claude for synthesis and verdict
5. Returns unified response

```python
# Pseudocode for the orchestration flow

async def analyze(property_data):
    # Parallel data fetching
    rent_task = fetch_rent_estimate(property_data)
    neighborhood_task = fetch_neighborhood(property_data.zip)
    comps_task = fetch_comps(property_data)

    rent, neighborhood, comps = await asyncio.gather(
        rent_task, neighborhood_task, comps_task
    )

    # Calculate investment metrics
    metrics = calculate_metrics(property_data, rent)

    # LLM synthesis
    verdict = await get_ai_verdict(property_data, rent, metrics, neighborhood, comps)

    return {
        "rent_estimate": rent,
        "metrics": metrics,
        "neighborhood": neighborhood,
        "comps": comps,
        "verdict": verdict
    }
```

---

## 4. Investment Calculations

### Cap Rate

```
Net Operating Income (NOI) = (Annual Rent) - (Taxes + Insurance + Maintenance + Vacancy + HOA)
Cap Rate = NOI / Purchase Price × 100

Assumptions (user-configurable):
  Vacancy Rate:    8%
  Maintenance:     1% of property value / year
  Insurance:       0.5% of property value / year
  Property Tax:    scraped from Zillow tax history, or 1.2% default
  Management Fee:  10% of gross rent (if investor doesn't self-manage)
```

### Cash Flow (with financing)

```
Monthly Mortgage = standard amortization formula
  Default: 30yr fixed, 7% rate, 25% down

Monthly Cash Flow = Monthly Rent - Mortgage - Taxes - Insurance - HOA
                    - Vacancy Reserve - Maintenance Reserve - Mgmt Fee

Annual Cash Flow = Monthly × 12
Cash-on-Cash Return = Annual Cash Flow / Total Cash Invested × 100
```

### BRRRR Analysis

```
Buy:        Purchase price
Rehab:      Estimated rehab cost (LLM estimates based on year_built, condition)
Rent:       Estimated monthly rent
Refinance:  75% LTV on After Repair Value (ARV = Zestimate or comp-based)
Repeat:     Cash left in deal = (Purchase + Rehab) - Refinance Amount

BRRRR Score:
  Excellent: Get all cash back + positive cash flow
  Good:      <10% cash left in deal + positive cash flow
  Fair:      <20% cash left in deal
  Poor:      >20% cash left in deal or negative cash flow
```

### Flip Potential

```
ARV (After Repair Value) = Zestimate or comp-based estimate
Rehab Cost = LLM estimate based on age, condition, sqft
Holding Costs = 6 months × (mortgage + taxes + insurance + utilities)
Selling Costs = 6% of ARV (agent commission) + 2% closing costs

Flip Profit = ARV - Purchase Price - Rehab - Holding Costs - Selling Costs
Flip ROI = Flip Profit / (Purchase Price + Rehab) × 100

Verdict:
  Excellent: ROI > 25%
  Good:      ROI 15-25%
  Marginal:  ROI 5-15%
  Avoid:     ROI < 5%
```

---

## 5. External APIs & Data Sources

### Rent Estimation

| Source          | What It Provides                   | Pricing                |
|-----------------|------------------------------------|------------------------|
| **Rentcast**    | Rent estimates, comps, market data | $50/mo (500 calls)     |
| **HUD FMR**     | Fair Market Rents by zip           | Free (government API)  |
| **Zillow ZORI** | Zillow Observed Rent Index         | Free (CSV download)    |

**Strategy:** Use Rentcast as primary source. Cross-reference with HUD FMR for
sanity check. Cache aggressively (rent data changes monthly, not daily).

### Neighborhood Data

| Source                  | Data                          | Pricing          |
|-------------------------|-------------------------------|------------------|
| **FBI Crime Data API**  | Crime rates by jurisdiction   | Free             |
| **GreatSchools API**    | School ratings (1-10)         | Free (with key)  |
| **Census Bureau API**   | Population, income, growth    | Free             |
| **FRED API**            | Economic indicators           | Free             |
| **BLS API**             | Employment, wage data         | Free             |
| **Redfin Data Center**  | Rent growth, market trends    | Free (CSV)       |

### Property / Comps

| Source                   | Data                        | Pricing               |
|--------------------------|-----------------------------|------------------------|
| **Rentcast**             | Comparable sales & rentals  | Included in plan       |
| **ATTOM Data**           | Property details, tax, AVM  | $299/mo (enterprise)   |
| **Zillow (scraped)**     | Zestimate, tax history      | Free (already on page) |

### AI

| Source                   | Use                          | Pricing               |
|--------------------------|------------------------------|-----------------------|
| **Claude API (Anthropic)** | Verdict synthesis, rehab estimates, narrative | Per-token |

---

## 6. LLM Analysis Layer

### Claude Prompt Structure

The LLM receives all gathered data and produces the final verdict.

```
System Prompt:
  You are a real estate investment analyst. Given property data, rental comps,
  investment metrics, and neighborhood data, provide a concise investment verdict.

User Prompt:
  PROPERTY: {address, price, sqft, beds, baths, year_built, type}
  RENT ESTIMATE: {estimated_rent, confidence, comps}
  INVESTMENT METRICS: {cap_rate, cash_flow, coc_return, brrrr_score, flip_roi}
  NEIGHBORHOOD: {crime_rate, school_rating, pop_growth, rent_growth, median_income}

  Provide:
  1. VERDICT: "Good Deal" | "Average" | "Avoid"
  2. CONFIDENCE: High | Medium | Low
  3. SUMMARY: 2-3 sentence explanation
  4. RISKS: Top 3 risks
  5. OPPORTUNITIES: Top 3 opportunities
  6. REHAB_ESTIMATE: Low/mid/high range based on year_built and property type
```

### When the LLM Adds Value (vs. Pure Calculation)

- **Rehab cost estimation** — no API gives this; LLM infers from age, type, sqft
- **Market narrative** — synthesizing crime + schools + growth into a story
- **Risk identification** — flags things like flood zones, declining markets
- **Deal comparison** — "This cap rate is below average for {zip}"
- **Nuanced verdict** — "Price is high but rent growth trajectory makes this viable in 2 years"

---

## 7. Caching Strategy

```
Layer 1: Extension (chrome.storage.local)
  - Cache full analysis results by Zillow property ID (zpid)
  - TTL: 24 hours
  - Max: 500 properties

Layer 2: Redis (backend)
  - Rent estimates by (zip, beds, baths): TTL 7 days
  - Neighborhood data by zip: TTL 30 days
  - Comps by address: TTL 3 days

Layer 3: Postgres (backend)
  - Historical analyses (for user history feature)
  - Aggregated market data (refreshed weekly via cron)
```

---

## 8. Side Panel UI Layout

```
┌─────────────────────────────────────┐
│  🏠 RealDeal AI                     │
│  123 Main St, Austin TX 78701       │
├─────────────────────────────────────┤
│                                     │
│  ██████████████████████             │
│  GOOD DEAL   (High Confidence)      │
│                                     │
│  "Strong rental yield in a growing  │
│   neighborhood. Below-market price  │
│   with 8.2% cap rate."             │
│                                     │
├─────────────────────────────────────┤
│  PROPERTY         │  RENT ESTIMATE  │
│  $285,000         │  $2,150/mo      │
│  3bd / 2ba        │  Confidence: 92%│
│  1,450 sqft       │                 │
│  Built: 1998      │  3 comps found  │
├─────────────────────────────────────┤
│  INVESTMENT METRICS                 │
│  ┌─────────┬──────────┬──────────┐  │
│  │Cap Rate │Cash Flow │ CoC Ret  │  │
│  │ 8.2%   │ $387/mo  │ 12.4%   │  │
│  └─────────┴──────────┴──────────┘  │
│                                     │
│  BRRRR: ★★★★☆  Cash left: $8,200   │
│  FLIP:  ★★★☆☆  Est. profit: $32K   │
├─────────────────────────────────────┤
│  NEIGHBORHOOD                       │
│  Crime:     ████████░░  Low         │
│  Schools:   ██████████  9/10        │
│  Pop Growth:██████░░░░  +2.1%/yr    │
│  Rent Growth:███████░░  +4.3%/yr    │
├─────────────────────────────────────┤
│  RISKS                              │
│  ⚠ HOA increased 15% last year      │
│  ⚠ Property tax above county avg    │
│                                     │
│  OPPORTUNITIES                      │
│  ✓ ADU potential (large lot)        │
│  ✓ Below Zestimate by 8%           │
├─────────────────────────────────────┤
│  ⚙ Customize Assumptions            │
│  Down payment: [25%]  Rate: [7.0%]  │
│  Vacancy: [8%]  Management: [10%]   │
└─────────────────────────────────────┘
```

---

## 9. Data Flow — Full Request Lifecycle

```
1. User navigates to zillow.com/homedetails/123-main-st/12345_zpid/

2. Content script detects URL match → scrapes property data
   Output: { zpid, address, price, sqft, beds, baths, year_built, ... }

3. Content script sends data to service worker via chrome.runtime.sendMessage

4. Service worker checks chrome.storage.local cache
   HIT  → return cached analysis to side panel
   MISS → proceed to step 5

5. Service worker sends POST /api/v1/analyze to backend

6. Backend orchestrates parallel fetches:
   ├── Rentcast API      → rent estimate + comps
   ├── FBI Crime API     → crime data
   ├── GreatSchools API  → school ratings
   ├── Census API        → demographics
   └── FRED/BLS API      → economic indicators

7. Backend calculates investment metrics (cap rate, cash flow, etc.)

8. Backend sends aggregated data to Claude API for verdict

9. Backend returns full analysis to extension

10. Service worker caches result, sends to side panel

11. Side panel renders metrics, charts, verdict
```

---

## 10. MVP Build Plan

### Phase 1 — Scraper + Static Metrics (Week 1-2)

**Goal:** Extension scrapes Zillow and shows basic calculations with hardcoded rent.

- [ ] Set up extension scaffolding (manifest, content script, side panel)
- [ ] Build DOM scraper with JSON-LD fallback
- [ ] Implement MutationObserver for SPA navigation
- [ ] Build side panel UI with static layout
- [ ] Hardcode rent-to-price ratio (1% rule) for initial metrics
- [ ] Calculate cap rate, cash flow, CoC return with user-adjustable assumptions
- [ ] Local-only, no backend needed

**Deliverable:** Installable extension that shows investment math on any Zillow listing.

### Phase 2 — Backend + Rent Estimation (Week 3-4)

**Goal:** Real rent estimates from API data.

- [ ] Set up FastAPI project with Docker
- [ ] Integrate Rentcast API for rent estimates and comps
- [ ] Integrate HUD Fair Market Rent as fallback
- [ ] Add Redis caching layer
- [ ] Connect extension to backend
- [ ] Display rent comps in side panel
- [ ] Add confidence score to rent estimate

**Deliverable:** Extension shows API-backed rent estimates with comparable properties.

### Phase 3 — Neighborhood Data (Week 5-6)

**Goal:** Contextual neighborhood intelligence.

- [ ] Integrate FBI Crime Data API
- [ ] Integrate GreatSchools API
- [ ] Integrate Census Bureau API for demographics
- [ ] Integrate FRED for economic indicators
- [ ] Build neighborhood section in side panel with visual bars
- [ ] Add Postgres for caching neighborhood data long-term

**Deliverable:** Full neighborhood context displayed alongside investment metrics.

### Phase 4 — AI Verdict (Week 7-8)

**Goal:** LLM-powered deal synthesis and verdict.

- [ ] Integrate Claude API
- [ ] Build prompt templates for verdict generation
- [ ] Add BRRRR analysis with LLM-estimated rehab costs
- [ ] Add flip analysis
- [ ] Build verdict UI component (color-coded badge + narrative)
- [ ] Add risk/opportunity bullets

**Deliverable:** Complete AI-powered analysis with Good Deal / Average / Avoid verdict.

### Phase 5 — Polish + Launch (Week 9-10)

- [ ] User accounts + API key management
- [ ] Saved properties / analysis history
- [ ] Export analysis as PDF
- [ ] Rate limiting and abuse prevention
- [ ] Error handling and loading states
- [ ] Chrome Web Store submission
- [ ] Landing page

---

## 11. Cost Estimates (Monthly, at scale)

| Component       | 1K users | 10K users | Notes                          |
|-----------------|----------|-----------|--------------------------------|
| Rentcast API    | $50      | $500      | Cached aggressively            |
| Claude API      | $30      | $250      | ~$0.03 per analysis            |
| Server (Fly.io) | $15      | $60       | FastAPI is lightweight          |
| Redis (Upstash) | $0       | $10       | Free tier covers MVP           |
| Postgres (Neon) | $0       | $19       | Free tier covers MVP           |
| **Total**       | **~$95** | **~$839** |                                |

Revenue model: Freemium. 3 free analyses/day, $9.99/mo for unlimited.

---

## 12. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Side panel vs popup | Side panel | Persistent UI alongside Zillow; doesn't obscure the listing |
| Manifest V3 | Yes | Required for new Chrome Web Store submissions |
| FastAPI over Flask | FastAPI | Native async for parallel API calls, auto OpenAPI docs |
| Claude over GPT | Claude | Better at structured analysis, more reliable JSON output |
| Rentcast over building own | Rentcast | Proven rent data; building comparable would take months |
| Redis + Postgres | Both | Redis for hot cache, Postgres for history and analytics |
| No frontend framework | Vanilla JS | Extension side panel is simple enough; avoids build complexity |
