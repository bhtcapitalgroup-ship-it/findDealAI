# RealDeal AI — API Documentation

**Base URL**: `https://api.realdeal-ai.com/api/v1`
**Authentication**: Bearer JWT token in `Authorization` header
**Content-Type**: `application/json`
**API Version**: v1

---

## Rate Limits

| Tier | Requests/min | Requests/day | Concurrent |
|------|-------------|-------------|------------|
| Free | 30 | 500 | 2 |
| Starter | 60 | 5,000 | 5 |
| Pro | 120 | 50,000 | 10 |
| Enterprise | 300 | Unlimited | 25 |

Rate limit headers are included in every response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1711036800
```

---

## Authentication

### POST `/auth/register`

Register a new user account.

**Auth Required**: No

**Request Body**:
```json
{
  "email": "investor@example.com",
  "password": "SecureP@ssw0rd!",
  "full_name": "Jane Investor",
  "phone": "+15551234567"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `email` | string | Yes | Valid email, max 255 chars |
| `password` | string | Yes | Min 8 chars, 1 uppercase, 1 number, 1 special |
| `full_name` | string | No | Max 255 chars |
| `phone` | string | No | E.164 format |

**Response** `201 Created`:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "investor@example.com",
  "full_name": "Jane Investor",
  "subscription_tier": "free",
  "is_verified": false,
  "created_at": "2026-03-16T10:00:00Z"
}
```

**Errors**: `409 Conflict` (email already exists), `422 Unprocessable Entity` (validation)

---

### POST `/auth/login`

Authenticate and receive JWT tokens.

**Auth Required**: No

**Request Body**:
```json
{
  "email": "investor@example.com",
  "password": "SecureP@ssw0rd!"
}
```

**Response** `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors**: `401 Unauthorized` (invalid credentials), `403 Forbidden` (account disabled)

---

### POST `/auth/refresh`

Refresh an expired access token.

**Auth Required**: No (refresh token in body)

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response** `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors**: `401 Unauthorized` (invalid/expired refresh token)

---

### POST `/auth/forgot-password`

Send a password reset email.

**Auth Required**: No

**Request Body**:
```json
{
  "email": "investor@example.com"
}
```

**Response** `202 Accepted`:
```json
{
  "message": "If an account exists with this email, a reset link has been sent."
}
```

---

### POST `/auth/reset-password`

Reset password using the token from the email link.

**Auth Required**: No

**Request Body**:
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecureP@ss1!"
}
```

**Response** `200 OK`:
```json
{
  "message": "Password has been reset successfully."
}
```

---

### POST `/auth/verify-email`

Verify email address with token sent during registration.

**Auth Required**: No

**Request Body**:
```json
{
  "token": "verification-token-from-email"
}
```

**Response** `200 OK`:
```json
{
  "message": "Email verified successfully."
}
```

---

## Properties

### GET `/properties`

Search and filter properties with pagination.

**Auth Required**: Yes (Free+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |
| `sort_by` | string | `investment_score` | Sort field: `investment_score`, `list_price`, `cap_rate`, `cash_on_cash`, `listed_at`, `price_per_sqft` |
| `sort_order` | string | `desc` | `asc` or `desc` |
| `state` | string | - | 2-letter state code (e.g., `TX`) |
| `city` | string | - | City name |
| `zip_code` | string | - | ZIP code (comma-separated for multiple) |
| `property_type` | string | - | Comma-separated: `single_family,multi_family,condo,...` |
| `listing_status` | string | `active` | Comma-separated: `active,pending,foreclosure,...` |
| `listing_source` | string | - | Comma-separated: `zillow,redfin,realtor,...` |
| `min_price` | number | - | Minimum list price |
| `max_price` | number | - | Maximum list price |
| `min_bedrooms` | int | - | Minimum bedrooms |
| `max_bedrooms` | int | - | Maximum bedrooms |
| `min_bathrooms` | number | - | Minimum bathrooms |
| `min_sqft` | int | - | Minimum square footage |
| `max_sqft` | int | - | Maximum square footage |
| `min_investment_score` | number | - | Minimum investment score (0-100) |
| `min_cap_rate` | number | - | Minimum cap rate (decimal, e.g., 0.06) |
| `min_cash_on_cash` | number | - | Minimum cash-on-cash return |
| `min_year_built` | int | - | Minimum year built |
| `lat` | number | - | Latitude for radius search |
| `lng` | number | - | Longitude for radius search |
| `radius_miles` | number | 10 | Search radius in miles (requires lat/lng) |
| `q` | string | - | Full-text search (address, city, description) |
| `listed_after` | datetime | - | ISO 8601 datetime |
| `listed_before` | datetime | - | ISO 8601 datetime |

**Response** `200 OK`:
```json
{
  "items": [
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "address_line1": "1234 Oak Street",
      "city": "Austin",
      "state": "TX",
      "zip_code": "78701",
      "latitude": 30.2672,
      "longitude": -97.7431,
      "property_type": "single_family",
      "listing_status": "active",
      "listing_source": "zillow",
      "list_price": 325000.00,
      "estimated_value": 340000.00,
      "estimated_rent": 2400.00,
      "bedrooms": 3,
      "bathrooms": 2.0,
      "sqft": 1650,
      "year_built": 1998,
      "investment_score": 82.5,
      "cap_rate": 6.2,
      "cash_on_cash": 8.1,
      "gross_yield": 8.86,
      "price_per_sqft": 196.97,
      "photos": ["https://photos.example.com/abc123/1.jpg"],
      "listed_at": "2026-03-10T14:30:00Z",
      "created_at": "2026-03-10T15:00:00Z"
    }
  ],
  "total": 1247,
  "page": 1,
  "per_page": 20,
  "pages": 63
}
```

**Tier Restrictions**:
- Free: max 50 results per search, no export, basic filters only
- Starter: max 500 results, all filters
- Pro: unlimited results, all filters, export
- Enterprise: unlimited, priority API access

---

### GET `/properties/{id}`

Get detailed property information including AI analysis.

**Auth Required**: Yes (Free+)

**Path Parameters**: `id` (UUID) — Property ID

**Response** `200 OK`:
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "address_line1": "1234 Oak Street",
  "address_line2": null,
  "city": "Austin",
  "state": "TX",
  "zip_code": "78701",
  "county": "Travis",
  "latitude": 30.2672,
  "longitude": -97.7431,
  "property_type": "single_family",
  "listing_status": "active",
  "listing_source": "zillow",
  "mls_number": "MLS-2026-12345",
  "listing_url": "https://www.zillow.com/homedetails/...",
  "list_price": 325000.00,
  "estimated_value": 340000.00,
  "last_sold_price": 275000.00,
  "last_sold_date": "2021-06-15",
  "estimated_rent": 2400.00,
  "hoa_fee": 0.00,
  "tax_annual": 5200.00,
  "insurance_annual": 1800.00,
  "bedrooms": 3,
  "bathrooms": 2.0,
  "sqft": 1650,
  "lot_sqft": 6500,
  "year_built": 1998,
  "stories": 1,
  "units": 1,
  "parking_spaces": 2,
  "description": "Beautifully updated 3-bedroom home in East Austin...",
  "photos": [
    "https://photos.example.com/abc123/1.jpg",
    "https://photos.example.com/abc123/2.jpg",
    "https://photos.example.com/abc123/3.jpg"
  ],
  "investment_score": 82.5,
  "cap_rate": 6.2,
  "cash_on_cash": 8.1,
  "gross_yield": 8.86,
  "price_per_sqft": 196.97,
  "rent_to_price_ratio": 0.00738,
  "ai_summary": "Strong investment opportunity in a rapidly appreciating East Austin neighborhood. Above-average cap rate for the area with solid rent-to-price ratio. Recent updates reduce near-term CapEx risk. Main risk: rising property taxes in Travis County.",
  "ai_analysis": {
    "strengths": [
      "Cap rate 1.5% above Austin metro median",
      "Recent renovations reduce maintenance risk",
      "Strong rental demand in 78701 ZIP"
    ],
    "risks": [
      "Travis County property taxes increasing 8% YoY",
      "Flood zone proximity (Zone X, low risk)",
      "Rising insurance costs in Texas"
    ],
    "comparable_properties": [
      {
        "address": "1456 Elm St, Austin, TX",
        "sold_price": 335000,
        "sold_date": "2026-02-20",
        "similarity_score": 0.92
      }
    ],
    "recommended_offer_range": {
      "conservative": 300000,
      "moderate": 315000,
      "aggressive": 325000
    }
  },
  "data_quality_score": 92.0,
  "last_scraped_at": "2026-03-16T08:00:00Z",
  "listed_at": "2026-03-10T14:30:00Z",
  "created_at": "2026-03-10T15:00:00Z",
  "updated_at": "2026-03-16T08:15:00Z"
}
```

**Errors**: `404 Not Found`

---

### GET `/properties/{id}/financials`

Get detailed financial projections for a property (Pro+).

**Auth Required**: Yes (Pro+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `down_payment_pct` | number | 25 | Down payment percentage |
| `interest_rate` | number | 7.0 | Mortgage interest rate |
| `loan_term_years` | int | 30 | Loan term in years |
| `vacancy_rate` | number | 5.0 | Expected vacancy percentage |
| `management_fee_pct` | number | 10.0 | Property management fee percentage |
| `maintenance_pct` | number | 1.0 | Annual maintenance as % of value |
| `annual_appreciation` | number | 3.0 | Expected annual appreciation % |
| `annual_rent_increase` | number | 2.5 | Expected annual rent increase % |

**Response** `200 OK`:
```json
{
  "property_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "purchase_assumptions": {
    "purchase_price": 325000.00,
    "down_payment": 81250.00,
    "closing_costs": 9750.00,
    "total_cash_needed": 91000.00,
    "loan_amount": 243750.00,
    "monthly_mortgage": 1621.45,
    "interest_rate": 7.0
  },
  "monthly_cash_flow": {
    "gross_rent": 2400.00,
    "vacancy_loss": -120.00,
    "effective_rent": 2280.00,
    "mortgage": -1621.45,
    "property_tax": -433.33,
    "insurance": -150.00,
    "hoa": 0.00,
    "management": -228.00,
    "maintenance": -270.83,
    "net_cash_flow": -423.61
  },
  "annual_returns": {
    "year_1": {
      "gross_rent": 28800,
      "noi": 21360,
      "cash_flow": -5083.32,
      "equity_buildup": 4850.00,
      "appreciation": 9750.00,
      "total_return": 9516.68,
      "cash_on_cash": -5.59,
      "total_roi": 10.46
    },
    "year_5": {
      "gross_rent": 31794,
      "noi": 23579,
      "cash_flow": -2244.12,
      "equity_buildup": 5890.00,
      "appreciation": 51342.00,
      "total_return": 54987.88,
      "cash_on_cash": -2.47,
      "total_roi": 60.43
    },
    "year_10": {
      "gross_rent": 35953,
      "noi": 26667,
      "cash_flow": 1543.68,
      "equity_buildup": 7650.00,
      "appreciation": 111848.00,
      "total_return": 121041.68,
      "cash_on_cash": 1.70,
      "total_roi": 133.01
    }
  },
  "break_even_month": 84
}
```

---

### GET `/properties/{id}/nearby`

Get nearby properties for comparison.

**Auth Required**: Yes (Starter+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `radius_miles` | number | 1 | Search radius |
| `limit` | int | 10 | Max results (max 50) |
| `similar_only` | bool | false | Filter to similar property type and size |

**Response** `200 OK`:
```json
{
  "center": {
    "property_id": "b2c3d4e5-...",
    "latitude": 30.2672,
    "longitude": -97.7431
  },
  "radius_miles": 1,
  "nearby": [
    {
      "id": "c3d4e5f6-...",
      "address_line1": "1456 Elm Street",
      "city": "Austin",
      "state": "TX",
      "list_price": 335000.00,
      "investment_score": 78.3,
      "distance_miles": 0.3,
      "property_type": "single_family",
      "bedrooms": 3,
      "bathrooms": 2.0,
      "sqft": 1720
    }
  ],
  "total": 8
}
```

---

## Deals (Saved Properties)

### GET `/deals`

List saved deals for the authenticated user.

**Auth Required**: Yes (Free+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page |
| `is_favorite` | bool | - | Filter favorites only |
| `label` | string | - | Filter by custom label |
| `sort_by` | string | `created_at` | `created_at`, `investment_score`, `list_price` |

**Response** `200 OK`:
```json
{
  "items": [
    {
      "id": "d4e5f6a7-...",
      "property": {
        "id": "b2c3d4e5-...",
        "address_line1": "1234 Oak Street",
        "city": "Austin",
        "state": "TX",
        "list_price": 325000.00,
        "investment_score": 82.5
      },
      "notes": "Great house hack candidate. Check flood zone.",
      "custom_label": "house_hack",
      "is_favorite": true,
      "offer_price": 310000.00,
      "created_at": "2026-03-15T09:00:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

**Tier Restrictions**:
- Free: max 10 saved deals
- Starter: max 100
- Pro: max 1,000
- Enterprise: unlimited

---

### POST `/deals`

Save a property as a deal.

**Auth Required**: Yes (Free+)

**Request Body**:
```json
{
  "property_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "notes": "Great house hack candidate.",
  "custom_label": "house_hack",
  "is_favorite": true,
  "offer_price": 310000.00
}
```

**Response** `201 Created`:
```json
{
  "id": "d4e5f6a7-...",
  "property_id": "b2c3d4e5-...",
  "notes": "Great house hack candidate.",
  "custom_label": "house_hack",
  "is_favorite": true,
  "offer_price": 310000.00,
  "created_at": "2026-03-16T10:00:00Z"
}
```

**Errors**: `409 Conflict` (already saved), `403 Forbidden` (tier limit reached)

---

### PUT `/deals/{id}`

Update a saved deal.

**Auth Required**: Yes (owner only)

**Request Body** (all fields optional):
```json
{
  "notes": "Updated notes after inspection.",
  "custom_label": "under_contract",
  "is_favorite": false,
  "offer_price": 305000.00,
  "custom_analysis": {
    "rehab_cost": 25000,
    "arv": 380000,
    "projected_rent": 2600
  }
}
```

**Response** `200 OK`: Updated deal object

---

### DELETE `/deals/{id}`

Remove a saved deal.

**Auth Required**: Yes (owner only)

**Response** `204 No Content`

---

### POST `/deals/compare`

Compare multiple saved deals side-by-side (Pro+).

**Auth Required**: Yes (Pro+)

**Request Body**:
```json
{
  "deal_ids": [
    "d4e5f6a7-...",
    "e5f6a7b8-...",
    "f6a7b8c9-..."
  ]
}
```

**Response** `200 OK`:
```json
{
  "deals": [
    {
      "deal_id": "d4e5f6a7-...",
      "address": "1234 Oak St, Austin, TX 78701",
      "list_price": 325000,
      "investment_score": 82.5,
      "cap_rate": 6.2,
      "cash_on_cash": 8.1,
      "estimated_rent": 2400,
      "price_per_sqft": 196.97,
      "bedrooms": 3,
      "sqft": 1650,
      "year_built": 1998
    }
  ],
  "recommendation": {
    "best_overall": "d4e5f6a7-...",
    "best_cash_flow": "e5f6a7b8-...",
    "best_appreciation": "f6a7b8c9-...",
    "ai_summary": "Property 1 (1234 Oak St) offers the best overall value with the highest investment score and cap rate. Property 2 edges ahead on monthly cash flow due to lower taxes. Property 3 is in a higher-appreciation neighborhood, making it better for long-term buy-and-hold."
  }
}
```

---

### GET `/deals/export`

Export saved deals to CSV or PDF (Pro+).

**Auth Required**: Yes (Pro+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `csv` | `csv` or `pdf` |
| `deal_ids` | string | - | Comma-separated IDs (all if omitted) |

**Response** `200 OK`: File download with appropriate `Content-Type`

---

## Alerts

### GET `/alerts`

List all alerts for the authenticated user.

**Auth Required**: Yes (Starter+)

**Response** `200 OK`:
```json
{
  "items": [
    {
      "id": "e5f6a7b8-...",
      "name": "Austin SFH Deals",
      "is_active": true,
      "channel": "email",
      "frequency": "instant",
      "criteria": {
        "cities": ["Austin"],
        "states": ["TX"],
        "property_types": ["single_family"],
        "min_price": 200000,
        "max_price": 400000,
        "min_investment_score": 70,
        "min_cap_rate": 0.05
      },
      "last_triggered_at": "2026-03-16T08:30:00Z",
      "trigger_count": 47,
      "created_at": "2026-02-01T12:00:00Z"
    }
  ],
  "total": 3
}
```

**Tier Restrictions**:
- Starter: 3 alerts, email only, daily digest only
- Pro: 20 alerts, all channels, instant + daily + weekly
- Enterprise: unlimited alerts, webhook support

---

### POST `/alerts`

Create a new alert.

**Auth Required**: Yes (Starter+)

**Request Body**:
```json
{
  "name": "Austin SFH Deals",
  "channel": "email",
  "frequency": "instant",
  "criteria": {
    "cities": ["Austin", "Round Rock"],
    "states": ["TX"],
    "property_types": ["single_family", "townhouse"],
    "min_price": 200000,
    "max_price": 400000,
    "min_bedrooms": 3,
    "min_investment_score": 70,
    "min_cap_rate": 0.05,
    "max_days_on_market": 14
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Alert display name |
| `channel` | string | Yes | `email`, `sms`, `push`, `webhook` |
| `frequency` | string | Yes | `instant`, `daily`, `weekly` |
| `criteria` | object | Yes | Filter criteria (see below) |

**Criteria fields** (all optional, at least one required):

| Field | Type | Description |
|-------|------|-------------|
| `zip_codes` | string[] | ZIP codes to monitor |
| `cities` | string[] | City names |
| `states` | string[] | 2-letter state codes |
| `property_types` | string[] | Property type enum values |
| `min_price` / `max_price` | number | Price range |
| `min_bedrooms` / `max_bedrooms` | int | Bedroom range |
| `min_bathrooms` | number | Minimum bathrooms |
| `min_sqft` / `max_sqft` | int | Square footage range |
| `min_investment_score` | number | Minimum score (0-100) |
| `min_cap_rate` | number | Minimum cap rate |
| `min_cash_on_cash` | number | Minimum cash-on-cash |
| `max_days_on_market` | int | Maximum days listed |
| `listing_sources` | string[] | Specific sources |

**Response** `201 Created`: Alert object

---

### PUT `/alerts/{id}`

Update an existing alert.

**Auth Required**: Yes (owner only)

**Request Body**: Same as POST (all fields optional)

**Response** `200 OK`: Updated alert object

---

### DELETE `/alerts/{id}`

Delete an alert.

**Auth Required**: Yes (owner only)

**Response** `204 No Content`

---

### POST `/alerts/{id}/test`

Trigger a test run to see what properties currently match.

**Auth Required**: Yes (owner only)

**Response** `200 OK`:
```json
{
  "alert_id": "e5f6a7b8-...",
  "matching_properties": 12,
  "sample": [
    {
      "id": "b2c3d4e5-...",
      "address_line1": "1234 Oak Street",
      "city": "Austin",
      "state": "TX",
      "list_price": 325000,
      "investment_score": 82.5
    }
  ]
}
```

---

## Markets

### GET `/markets`

Get market data for a geographic area.

**Auth Required**: Yes (Free+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zip_code` | string | - | ZIP code |
| `city` | string | - | City name (requires state) |
| `state` | string | - | 2-letter state code |
| `period` | string | `latest` | `latest`, `3m`, `6m`, `1y`, `2y` |

**Response** `200 OK`:
```json
{
  "location": {
    "zip_code": "78701",
    "city": "Austin",
    "state": "TX",
    "county": "Travis"
  },
  "period": {
    "start": "2026-02-01",
    "end": "2026-02-28"
  },
  "metrics": {
    "median_list_price": 425000,
    "median_sold_price": 410000,
    "median_rent": 2200,
    "median_dom": 28,
    "inventory_count": 1450,
    "new_listings_count": 380,
    "sold_count": 290,
    "price_per_sqft": 245.50,
    "sale_to_list_ratio": 0.9647,
    "price_change_yoy": 4.2,
    "rent_change_yoy": 3.8,
    "vacancy_rate": 0.054,
    "population": 1028225,
    "median_income": 78500,
    "unemployment_rate": 0.032
  },
  "market_score": 74.5,
  "trend_direction": "appreciating",
  "ai_insights": {
    "summary": "Austin remains a strong market for buy-and-hold investors. Rent growth outpacing national average. New supply coming online in 2026 may moderate price appreciation.",
    "investment_outlook": "positive",
    "top_zip_codes": ["78702", "78745", "78748"]
  }
}
```

---

### GET `/markets/compare`

Compare multiple markets side-by-side.

**Auth Required**: Yes (Starter+)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zip_codes` | string | Yes | Comma-separated ZIP codes (max 5) |
| `period` | string | No | Time period (default: `latest`) |

**Response** `200 OK`:
```json
{
  "markets": [
    {
      "zip_code": "78701",
      "city": "Austin",
      "state": "TX",
      "median_list_price": 425000,
      "median_rent": 2200,
      "cap_rate_avg": 5.8,
      "price_change_yoy": 4.2,
      "market_score": 74.5
    },
    {
      "zip_code": "37206",
      "city": "Nashville",
      "state": "TN",
      "median_list_price": 380000,
      "median_rent": 2050,
      "cap_rate_avg": 6.1,
      "price_change_yoy": 5.1,
      "market_score": 78.2
    }
  ],
  "recommendation": "Nashville (37206) currently offers better value with a higher average cap rate and stronger appreciation trend, though Austin (78701) has a deeper rental market."
}
```

---

### GET `/markets/trends`

Get historical trend data for charting.

**Auth Required**: Yes (Starter+)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zip_code` | string | - | ZIP code (required) |
| `metric` | string | `median_list_price` | Metric to trend |
| `period` | string | `1y` | `3m`, `6m`, `1y`, `2y`, `5y` |
| `granularity` | string | `monthly` | `weekly`, `monthly`, `quarterly` |

**Response** `200 OK`:
```json
{
  "zip_code": "78701",
  "metric": "median_list_price",
  "period": "1y",
  "data_points": [
    { "date": "2025-03-01", "value": 408000 },
    { "date": "2025-04-01", "value": 412000 },
    { "date": "2025-05-01", "value": 415000 },
    { "date": "2025-06-01", "value": 418000 },
    { "date": "2025-07-01", "value": 420000 },
    { "date": "2025-08-01", "value": 419000 },
    { "date": "2025-09-01", "value": 417000 },
    { "date": "2025-10-01", "value": 418000 },
    { "date": "2025-11-01", "value": 420000 },
    { "date": "2025-12-01", "value": 421000 },
    { "date": "2026-01-01", "value": 423000 },
    { "date": "2026-02-01", "value": 425000 }
  ]
}
```

---

## Users

### GET `/users/me`

Get current user profile.

**Auth Required**: Yes

**Response** `200 OK`:
```json
{
  "id": "a1b2c3d4-...",
  "email": "investor@example.com",
  "full_name": "Jane Investor",
  "phone": "+15551234567",
  "subscription_tier": "pro",
  "is_verified": true,
  "saved_deals_count": 12,
  "alerts_count": 3,
  "created_at": "2026-01-15T10:00:00Z",
  "last_login_at": "2026-03-16T09:00:00Z"
}
```

---

### PUT `/users/me`

Update current user profile.

**Auth Required**: Yes

**Request Body**:
```json
{
  "full_name": "Jane M. Investor",
  "phone": "+15559876543"
}
```

**Response** `200 OK`: Updated user object

---

### PUT `/users/me/password`

Change password.

**Auth Required**: Yes

**Request Body**:
```json
{
  "current_password": "OldP@ssw0rd!",
  "new_password": "NewP@ssw0rd!"
}
```

**Response** `200 OK`:
```json
{
  "message": "Password updated successfully."
}
```

---

### GET `/users/me/subscription`

Get subscription details.

**Auth Required**: Yes

**Response** `200 OK`:
```json
{
  "tier": "pro",
  "status": "active",
  "current_period_start": "2026-03-01T00:00:00Z",
  "current_period_end": "2026-04-01T00:00:00Z",
  "cancel_at_period_end": false,
  "usage": {
    "saved_deals": { "used": 12, "limit": 1000 },
    "alerts": { "used": 3, "limit": 20 },
    "api_calls_today": { "used": 450, "limit": 50000 },
    "exports_this_month": { "used": 2, "limit": null }
  }
}
```

---

### POST `/users/me/subscription`

Create or update subscription (initiates Stripe checkout).

**Auth Required**: Yes

**Request Body**:
```json
{
  "tier": "pro",
  "billing_cycle": "monthly"
}
```

**Response** `200 OK`:
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "session_id": "cs_test_..."
}
```

---

### POST `/users/me/subscription/cancel`

Cancel subscription at end of billing period.

**Auth Required**: Yes

**Response** `200 OK`:
```json
{
  "message": "Subscription will be cancelled at the end of the current billing period.",
  "cancel_at": "2026-04-01T00:00:00Z"
}
```

---

## WebSocket

### WS `/ws/alerts`

Real-time deal alert notifications.

**Auth**: JWT token as query parameter: `/ws/alerts?token=eyJ...`

**Server Messages**:
```json
{
  "type": "new_deal",
  "alert_id": "e5f6a7b8-...",
  "alert_name": "Austin SFH Deals",
  "property": {
    "id": "b2c3d4e5-...",
    "address_line1": "1234 Oak Street",
    "city": "Austin",
    "state": "TX",
    "list_price": 325000,
    "investment_score": 82.5
  },
  "timestamp": "2026-03-16T10:15:00Z"
}
```

**Client Messages**:
```json
{
  "type": "ping"
}
```

**Server Heartbeat**: Every 30 seconds
```json
{
  "type": "pong",
  "timestamp": "2026-03-16T10:15:30Z"
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format."
      }
    ]
  }
}
```

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `BAD_REQUEST` | Malformed request |
| 401 | `UNAUTHORIZED` | Missing or invalid token |
| 403 | `FORBIDDEN` | Insufficient permissions or tier |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Duplicate resource |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 429 | `RATE_LIMITED` | Rate limit exceeded |
| 500 | `INTERNAL_ERROR` | Server error |
