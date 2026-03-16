# RealDeal AI — Scraping Pipeline Documentation

## Architecture Overview

```
+----------------+     +--------------+     +------------------+
|  Celery Beat   |---->|  Redis       |---->|  Worker Pool     |
|  (Scheduler)   |     |  (Task Queue)|     |  (8 concurrent)  |
+----------------+     +--------------+     +--------+---------+
                                                     |
                                            +--------v---------+
                                            |   Proxy Layer     |
                                            |   (BrightData)    |
                                            |   Residential IPs |
                                            +--------+---------+
                                                     |
                              +----------------------+----------------------+
                              |                      |                      |
                     +--------v------+    +----------v----+    +-----------v---+
                     |    Zillow     |    |    Redfin     |    |  Realtor.com  |
                     |    Parser     |    |    Parser     |    |    Parser     |
                     +--------+------+    +----------+----+    +-----------+---+
                              |                      |                      |
                              +----------------------+----------------------+
                                                     |
                                            +--------v---------+
                                            |  Normalization    |
                                            |  Pipeline         |
                                            +--------+---------+
                                                     |
                                            +--------v---------+
                                            |  Deduplication    |
                                            |  Engine           |
                                            +--------+---------+
                                                     |
                                            +--------v---------+
                                            |  PostgreSQL       |
                                            |  (Upsert)        |
                                            +------------------+
```

---

## Scheduling Strategy

### Priority Tiers

| Tier | Markets | Scrape Frequency | Rationale |
|------|---------|-----------------|-----------|
| P0 (Hot) | Top 10 metros by user count | Every 2 hours | Highest user demand, most competitive |
| P1 (Warm) | Top 11-30 metros | Every 6 hours | Good coverage, moderate demand |
| P2 (Standard) | Top 31-100 metros | Every 12 hours | Baseline coverage |
| P3 (Long-tail) | All other ZIP codes | Every 24 hours | Comprehensive but lower priority |

### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    "scrape-p0-markets": {
        "task": "app.tasks.scraping.scrape_tier",
        "schedule": crontab(minute="0", hour="*/2"),  # Every 2 hours
        "args": ("P0",),
        "options": {"queue": "scraping", "priority": 9},
    },
    "scrape-p1-markets": {
        "task": "app.tasks.scraping.scrape_tier",
        "schedule": crontab(minute="30", hour="*/6"),  # Every 6 hours
        "args": ("P1",),
        "options": {"queue": "scraping", "priority": 6},
    },
    "scrape-p2-markets": {
        "task": "app.tasks.scraping.scrape_tier",
        "schedule": crontab(minute="0", hour="*/12"),  # Every 12 hours
        "args": ("P2",),
        "options": {"queue": "scraping", "priority": 3},
    },
    "scrape-p3-markets": {
        "task": "app.tasks.scraping.scrape_tier",
        "schedule": crontab(minute="0", hour="3"),  # Daily at 3 AM
        "args": ("P3",),
        "options": {"queue": "scraping", "priority": 1},
    },
}
```

---

## Per-Source Scraping Strategy

### Zillow

| Attribute | Detail |
|-----------|--------|
| Method | HTTP requests to Zillow's search API endpoints |
| Data Format | JSON responses from internal API |
| Rate Limit | 2-3 requests/second per IP |
| Proxy Required | Yes (residential) |
| Anti-Bot | Sophisticated — requires valid headers, cookie management, captcha on suspicious behavior |
| Data Available | List price, address, beds/baths/sqft, photos, days on market, Zestimate, price history, tax data |
| Pagination | Cursor-based, max 40 results per page |
| Coverage | ~110M properties nationwide |

**Strategy**:
1. Search by ZIP code with filters (for_sale, recently_sold)
2. Parse search results JSON for listing IDs
3. Fetch individual property details for enriched data
4. Extract Zestimate as `estimated_value`

**Key Selectors/Endpoints**:
```
Search: /search/GetSearchPageState.htm?searchQueryState={...}
Detail: /homedetails/{address}/{zpid}_zpid/
```

### Redfin

| Attribute | Detail |
|-----------|--------|
| Method | Redfin's internal "stingray" API |
| Data Format | JSON (prefixed with comment block, needs stripping) |
| Rate Limit | 1-2 requests/second per IP |
| Proxy Required | Yes (residential) |
| Anti-Bot | Moderate — header validation, rate-based blocking |
| Data Available | List price, address, beds/baths/sqft, Redfin estimate, HOA, lot size, year built, market insights |
| Pagination | Offset-based, max 350 results per query |
| Coverage | ~100M properties |

**Strategy**:
1. Use Redfin's search autocomplete to get region IDs
2. Query `/api/gis?...` with region ID and filters
3. Parse property listing details
4. Redfin estimate used as secondary `estimated_value`

**Key Endpoints**:
```
Search: /stingray/api/gis?al=1&region_id={id}&region_type=6&...
Detail: /stingray/api/home/details/belowTheFold?propertyId={id}
```

### Realtor.com

| Attribute | Detail |
|-----------|--------|
| Method | GraphQL API |
| Data Format | JSON (GraphQL response) |
| Rate Limit | 2-4 requests/second per IP |
| Proxy Required | Yes (residential) |
| Anti-Bot | Moderate — fingerprinting, rate limiting |
| Data Available | List price, address, beds/baths/sqft, photos, description, broker info, open houses |
| Pagination | Offset-based, max 200 results per query |
| Coverage | ~135M properties (largest MLS coverage) |

**Strategy**:
1. Send GraphQL query with ZIP code and filters
2. Extract `property_id` from search results
3. Fetch individual property details via GraphQL
4. Realtor.com often has the most complete listing descriptions

**Key Endpoints**:
```
GraphQL: /api/v1/hulk?client_id=rdc-x&schema=vesta
```

### Rentometer

| Attribute | Detail |
|-----------|--------|
| Method | API (official partner API preferred) or scraping fallback |
| Data Format | JSON |
| Rate Limit | Depends on plan |
| Proxy Required | Only for scraping fallback |
| Data Available | Median rent, rent range (25th-75th percentile), sample size, by bedroom count |
| Coverage | Most US ZIP codes |

**Strategy**:
1. Query by address or ZIP code + bedroom count
2. Extract median rent and confidence interval
3. Use as `estimated_rent` when listing rent data is unavailable

**Note**: Prefer official API partnership. Scraping is the fallback only.

### Public Records (County Assessor)

| Attribute | Detail |
|-----------|--------|
| Method | Varies by county — some have APIs, most require HTML parsing |
| Data Format | HTML (county-specific) |
| Rate Limit | Generally lenient (government sites) |
| Proxy Required | Usually no |
| Data Available | Tax assessed value, tax amount, owner name, deed history, legal description, lot dimensions |
| Coverage | County-by-county (start with top 50 counties by user demand) |

**Strategy**:
1. Maintain per-county parser configurations
2. Look up by address (parsed from listing data)
3. Extract tax data and assessed value
4. Use for `tax_annual` and as a valuation cross-reference

---

## Anti-Detection Measures

### Proxy Rotation

```python
class ProxyManager:
    """Manages BrightData residential proxy rotation."""

    def __init__(self):
        self.zone = os.getenv("BRIGHTDATA_ZONE", "residential")
        self.host = os.getenv("BRIGHTDATA_HOST", "brd.superproxy.io")
        self.port = int(os.getenv("BRIGHTDATA_PORT", 22225))

    def get_proxy(self, country="us", state=None, city=None):
        """Get a rotating residential proxy, optionally geo-targeted."""
        username = f"brd-customer-{CUSTOMER_ID}-zone-{self.zone}"
        if country:
            username += f"-country-{country}"
        if state:
            username += f"-state-{state}"
        if city:
            username += f"-city-{city}"

        return {
            "http": f"http://{username}:{PASSWORD}@{self.host}:{self.port}",
            "https": f"http://{username}:{PASSWORD}@{self.host}:{self.port}",
        }
```

**Rotation Rules**:
- New IP for every request to the same domain
- Geo-target proxies to the state being scraped (appears more natural)
- Maintain a blocklist of IPs that received captchas/blocks

### Request Throttling

| Source | Min Delay | Max Delay | Concurrent Requests |
|--------|-----------|-----------|-------------------|
| Zillow | 3s | 8s | 2 per worker |
| Redfin | 2s | 6s | 3 per worker |
| Realtor.com | 2s | 5s | 3 per worker |
| Public Records | 1s | 3s | 5 per worker |

Delays are randomized within the range using a Poisson distribution to avoid periodic patterns.

### Browser Fingerprint Randomization

Each request includes randomized headers to mimic real browser traffic:

```python
def get_random_headers():
    """Generate realistic randomized browser headers."""
    chrome_versions = ["120.0.6099.109", "121.0.6167.85", "122.0.6261.69", "123.0.6312.58"]
    os_versions = [
        "Windows NT 10.0; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_7",
        "X11; Linux x86_64",
        "Macintosh; Intel Mac OS X 13_6_3",
    ]
    languages = ["en-US,en;q=0.9", "en-US,en;q=0.8", "en-GB,en;q=0.9,en-US;q=0.8"]

    chrome_ver = random.choice(chrome_versions)
    os_ver = random.choice(os_versions)

    return {
        "User-Agent": f"Mozilla/5.0 ({os_ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(languages),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": random.choice(["1", "0"]),
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua-Platform": f'"{random.choice(["Windows", "macOS", "Linux"])}"',
    }
```

### Additional Anti-Detection Measures

| Measure | Implementation |
|---------|---------------|
| Cookie persistence | Maintain session cookies across requests to the same domain within a task |
| Referer chain | Simulate natural navigation (homepage -> search -> listing) |
| Request timing | Add random micro-delays (100-500ms) to simulate human reading |
| Viewport randomization | Set random viewport dimensions in headless browser requests |
| JavaScript rendering | Use Playwright/Puppeteer for sites requiring JS (fallback only — slower) |
| Captcha solving | BrightData CAPTCHA solver for occasional captchas (~$2-5 per 1K solves) |

---

## Data Normalization Pipeline

### Step 1: Address Standardization

```python
def normalize_address(raw_address: dict) -> dict:
    """Standardize address components across all sources."""
    return {
        "address_line1": standardize_street(raw_address.get("street", "")),
        "address_line2": raw_address.get("unit", None),
        "city": raw_address.get("city", "").strip().title(),
        "state": normalize_state(raw_address.get("state", "")),  # "California" -> "CA"
        "zip_code": raw_address.get("zip", "")[:5],  # Normalize to 5-digit
        "county": raw_address.get("county", "").strip().title(),
    }

def standardize_street(street: str) -> str:
    """Normalize street abbreviations and formatting."""
    replacements = {
        r"\bSt\b": "Street", r"\bAve\b": "Avenue", r"\bBlvd\b": "Boulevard",
        r"\bDr\b": "Drive", r"\bLn\b": "Lane", r"\bRd\b": "Road",
        r"\bCt\b": "Court", r"\bPl\b": "Place", r"\bCir\b": "Circle",
        r"\bPkwy\b": "Parkway", r"\bHwy\b": "Highway",
        r"\bApt\b": "Apartment", r"\bSte\b": "Suite", r"\bUnt\b": "Unit",
    }
    for pattern, replacement in replacements.items():
        street = re.sub(pattern, replacement, street, flags=re.IGNORECASE)
    return street.strip().title()
```

### Step 2: Data Type Normalization

| Field | Normalization Rule |
|-------|-------------------|
| `list_price` | Strip `$`, commas, convert to Decimal. "$325,000" -> 325000.00 |
| `sqft` | Strip commas, "sq ft", convert to int. "1,650 sq ft" -> 1650 |
| `bathrooms` | Parse "2 full, 1 half" -> 2.5 |
| `year_built` | Validate range (1700-2027), null if invalid |
| `lot_sqft` | Convert acres to sqft if needed (1 acre = 43,560 sqft) |
| `listed_at` | Parse to UTC datetime, handle relative dates ("3 days ago") |
| `photos` | Normalize to list of full URLs, remove query params |
| `description` | Strip HTML tags, normalize whitespace, truncate to 5000 chars |

### Step 3: Source-Specific Field Mapping

```python
# Each source parser outputs a SourceListing dataclass
# which is then mapped to the normalized PropertyData schema

FIELD_MAPPING = {
    "zillow": {
        "zpid": "source_id",
        "price": "list_price",
        "zestimate": "estimated_value",
        "bedrooms": "bedrooms",
        "bathrooms": "bathrooms",
        "livingArea": "sqft",
        "lotSize": "lot_sqft",
        "yearBuilt": "year_built",
        "homeType": "property_type",
        "homeStatus": "listing_status",
        "daysOnZillow": "_days_on_market",
    },
    "redfin": {
        "propertyId": "source_id",
        "price.value": "list_price",
        "predictedValue": "estimated_value",
        "beds": "bedrooms",
        "baths": "bathrooms",
        "sqFt.value": "sqft",
        "lotSqFt": "lot_sqft",
        "yearBuilt": "year_built",
        "propertyType": "property_type",
        "listingType": "listing_status",
    },
    # ... similar for realtor.com
}
```

### Step 4: Property Type Normalization

| Source Value | Normalized Enum |
|-------------|----------------|
| "SINGLE_FAMILY", "SingleFamily", "House" | `single_family` |
| "MULTI_FAMILY", "MultiFamily", "Duplex", "Triplex", "Quadruplex" | `multi_family` |
| "CONDO", "Condominium", "Co-op" | `condo` |
| "TOWNHOUSE", "Townhome", "RowHouse" | `townhouse` |
| "LAND", "Lot", "Vacant Land" | `land` |
| "COMMERCIAL", "Office", "Retail" | `commercial` |
| "MANUFACTURED", "Mobile Home" | `mobile_home` |

---

## Deduplication Strategy

### Three-Level Deduplication

#### Level 1: MLS Number (Exact Match)

```sql
-- O(1) lookup via unique index
SELECT id FROM properties WHERE mls_number = $1;
```

If a match is found, the existing record is **updated** with fresh data from the new scrape.

#### Level 2: Address + ZIP Code (Exact Match)

```sql
SELECT id FROM properties
WHERE zip_code = $1
  AND lower(address_line1) = lower($2);
```

Catches listings that appear on multiple sources without an MLS number.

#### Level 3: Address Fuzzy Match (Trigram Similarity)

```sql
SELECT id, address_line1,
       similarity(address_line1, $1) AS sim
FROM properties
WHERE zip_code = $2
  AND address_line1 % $1       -- trigram similarity > 0.3
  AND similarity(address_line1, $1) > 0.85
ORDER BY sim DESC
LIMIT 1;
```

Catches variations like:
- "123 Main Street" vs "123 Main St"
- "456 Oak Avenue #2" vs "456 Oak Ave, Unit 2"
- "789 Elm Boulevard" vs "789 Elm Blvd."

#### Decision Logic

```python
async def deduplicate(new_listing: PropertyData) -> tuple[str, UUID | None]:
    """
    Returns:
        ("insert", None)           - New property, insert it
        ("update", existing_id)    - Duplicate found, update existing
        ("skip", existing_id)      - Duplicate with no new data
    """
    # Level 1: MLS exact match
    if new_listing.mls_number:
        existing = await find_by_mls(new_listing.mls_number)
        if existing:
            if has_new_data(existing, new_listing):
                return ("update", existing.id)
            return ("skip", existing.id)

    # Level 2: Address exact match
    existing = await find_by_exact_address(
        new_listing.address_line1, new_listing.zip_code
    )
    if existing:
        if has_new_data(existing, new_listing):
            return ("update", existing.id)
        return ("skip", existing.id)

    # Level 3: Fuzzy address match
    existing = await find_by_fuzzy_address(
        new_listing.address_line1, new_listing.zip_code, threshold=0.85
    )
    if existing:
        if has_new_data(existing, new_listing):
            return ("update", existing.id)
        return ("skip", existing.id)

    return ("insert", None)
```

---

## Legal Considerations and Compliance

### robots.txt Compliance

| Site | robots.txt Policy | Our Approach |
|------|------------------|-------------|
| Zillow | Disallows many paths for bots | We access publicly available data; rate-limit to be respectful |
| Redfin | Standard bot restrictions | Respectful rate limiting, no aggressive crawling |
| Realtor.com | Standard restrictions | Respectful rate limiting |
| Public Records | Generally permissive | Standard crawling |

### Terms of Service

**Disclaimer**: Web scraping exists in a legal gray area. The following considerations guide our approach:

1. **Public data**: We only scrape publicly available listing data that any person can view in a browser without logging in.

2. **No circumvention**: We do not bypass authentication, CAPTCHAs (beyond standard solving), or other access controls.

3. **Rate limiting**: Our request rates are designed to be indistinguishable from normal browsing patterns and do not create undue server load.

4. **Data use**: We aggregate and transform data for investment analysis — we do not republish raw listings or compete directly with the source platforms.

5. **CFAA considerations**: The Computer Fraud and Abuse Act has been narrowed by recent court decisions (Van Buren v. United States, 2021). Accessing publicly available data without circumventing access controls is generally permissible.

6. **hiQ Labs v. LinkedIn precedent**: Scraping publicly available data has been upheld by courts, though the legal landscape continues to evolve.

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Cease and desist letter | Immediately comply, remove data from that source, consult legal counsel |
| IP blocking | Proxy rotation, but also take it as a signal to reduce load |
| Legal action | $10K legal reserve, D&O insurance, corporate structure (LLC) |
| Data licensing availability | Prefer licensed data feeds (MLS, Rentometer API) when cost-effective |
| Regulatory changes | Monitor legal developments, maintain ability to pivot to licensed data |

### Long-Term Data Strategy

The scraping approach is designed as a **bootstrap strategy**. The long-term plan:

1. **Months 1-6**: Scrape to build initial dataset and prove product-market fit
2. **Months 6-12**: Pursue MLS data partnerships (IDX/RETS feeds) in top markets
3. **Year 2+**: Licensed data feeds as primary source, scraping as supplement for non-MLS data

---

## Failure Handling and Monitoring

### Retry Strategy

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,        # Exponential backoff
    retry_backoff_max=600,     # Max 10 minutes between retries
    retry_jitter=True,         # Add randomness to prevent thundering herd
    rate_limit="10/m",         # Max 10 tasks per minute per worker
    acks_late=True,            # Re-queue if worker crashes
    reject_on_worker_lost=True,
)
def scrape_listing(self, source: str, region: str, params: dict):
    try:
        result = execute_scrape(source, region, params)
        return result
    except RateLimitError:
        # Exponential backoff with jitter
        raise self.retry(countdown=random.uniform(30, 120))
    except ProxyBlockedError:
        # Rotate proxy and retry immediately
        raise self.retry(countdown=5)
    except CaptchaError:
        # Log and retry with different proxy
        logger.warning(f"CAPTCHA on {source} for {region}")
        raise self.retry(countdown=random.uniform(60, 300))
    except ParserError as e:
        # Don't retry parser errors — they indicate site structure changed
        logger.error(f"Parser error on {source}: {e}")
        alert_ops_team(f"Parser broken for {source}: {e}")
        raise  # Dead letter queue
    except Exception as e:
        logger.exception(f"Unexpected error scraping {source}/{region}")
        raise self.retry(exc=e)
```

### Monitoring Dashboard

| Metric | Alert Threshold | Check Frequency |
|--------|----------------|-----------------|
| Scrape success rate (per source) | < 90% over 1 hour | Every 5 minutes |
| Average scrape latency | > 10s per page | Every 5 minutes |
| New listings per hour | < 50% of 7-day average | Every hour |
| Proxy error rate | > 20% | Every 5 minutes |
| Parser error rate | > 5% | Every 5 minutes |
| Queue depth (scraping) | > 10,000 tasks | Every minute |
| Worker memory usage | > 80% | Every minute |
| Database insert rate | < 50% of expected | Every 15 minutes |

### Health Check Queries

```sql
-- Data freshness: last scrape per source
SELECT listing_source,
       MAX(last_scraped_at) as last_scrape,
       COUNT(*) FILTER (WHERE last_scraped_at > now() - interval '24 hours') as scraped_24h
FROM properties
GROUP BY listing_source;

-- Data quality: completeness metrics
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE list_price IS NOT NULL) as has_price,
    COUNT(*) FILTER (WHERE estimated_rent IS NOT NULL) as has_rent,
    COUNT(*) FILTER (WHERE investment_score IS NOT NULL) as has_score,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL) as has_geo,
    ROUND(AVG(data_quality_score), 1) as avg_quality
FROM properties
WHERE listing_status = 'active';
```

---

## Cost Per Listing Estimate

### Proxy + Compute Cost Breakdown

| Component | Cost per 1,000 Listings | Notes |
|-----------|------------------------|-------|
| Proxy bandwidth (BrightData) | $0.50-1.50 | ~3 pages per listing x ~200 KB |
| Compute (Celery worker time) | $0.05-0.10 | ~2 seconds per listing |
| AI analysis (GPT-4o-mini) | $0.40 | ~800 tokens per listing |
| AI analysis (GPT-4o, for top deals) | $2.00 | Only top 10% of listings |
| Database storage | $0.01 | ~5 KB per listing |
| **Total (basic)** | **$0.96-2.01** | Per 1,000 listings |
| **Total (with AI)** | **$1.36-3.51** | Per 1,000 listings |

### Monthly Cost at Scale

| Volume | Proxy | Compute | AI | Storage | Total |
|--------|-------|---------|-----|---------|-------|
| 50K listings/mo | $50 | $5 | $30 | $1 | **$86** |
| 200K listings/mo | $200 | $15 | $100 | $3 | **$318** |
| 1M listings/mo | $1,000 | $75 | $400 | $10 | **$1,485** |

These costs represent excellent unit economics — at $79/mo per Pro user, each user's subscription covers the scraping cost for ~22,000-56,000 listings.
