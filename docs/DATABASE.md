# RealDeal AI — Database Schema Documentation

## Overview

RealDeal AI uses **PostgreSQL 16** with the **PostGIS** extension for geospatial queries, **pg_trgm** for fuzzy text matching, and native **JSONB** for flexible semi-structured data. All primary keys are UUIDs generated server-side.

---

## ER Diagram

```
+-------------------+          +---------------------+
|      users        |          |     properties      |
+-------------------+          +---------------------+
| id (PK, UUID)     |    +----| id (PK, UUID)       |
| email (UNIQUE)    |    |    | address_line1       |
| hashed_password   |    |    | address_line2       |
| full_name         |    |    | city                |
| phone             |    |    | state               |
| subscription_tier |    |    | zip_code            |
| stripe_customer_id|    |    | county              |
| stripe_sub_id     |    |    | latitude            |
| is_active         |    |    | longitude           |
| is_verified       |    |    | location (GEOGRAPHY)|
| is_superuser      |    |    | property_type       |
| last_login_at     |    |    | listing_status      |
| created_at        |    |    | listing_source      |
| updated_at        |    |    | mls_number (UNIQUE) |
+--------+----------+    |    | listing_url         |
         |               |    | list_price          |
         |  1        N   |    | estimated_value     |
         +------+--------+    | last_sold_price     |
         |      |              | last_sold_date      |
         |      |              | estimated_rent      |
         v      v              | hoa_fee             |
+--------+------+--------+    | tax_annual          |
|    saved_deals          |    | insurance_annual    |
+-------------------------+    | bedrooms            |
| id (PK, UUID)           |    | bathrooms           |
| user_id (FK -> users)   +----+ sqft                |
| property_id (FK -> prop) |    | lot_sqft            |
| notes                    |    | year_built          |
| custom_label             |    | stories             |
| is_favorite              |    | units               |
| custom_analysis (JSONB)  |    | parking_spaces      |
| offer_price              |    | description         |
| created_at               |    | photos (JSONB)      |
| updated_at               |    | investment_score    |
+-------------------------+    | cap_rate            |
                               | cash_on_cash        |
+-------------------+          | gross_yield         |
|      alerts       |          | price_per_sqft      |
+-------------------+          | rent_to_price_ratio |
| id (PK, UUID)     |          | ai_summary          |
| user_id (FK)   ---+---> users| ai_analysis (JSONB) |
| name              |          | raw_data (JSONB)    |
| is_active         |          | data_quality_score  |
| channel           |          | last_scraped_at     |
| criteria (JSONB)  |          | listed_at           |
| frequency         |          | created_at          |
| last_triggered_at |          | updated_at          |
| trigger_count     |          +---------------------+
| created_at        |
| updated_at        |          +---------------------+
+-------------------+          |    market_data      |
                               +---------------------+
                               | id (PK, UUID)       |
                               | zip_code            |
                               | city                |
                               | state               |
                               | county              |
                               | period_start        |
                               | period_end          |
                               | median_list_price   |
                               | median_sold_price   |
                               | median_rent         |
                               | median_dom          |
                               | inventory_count     |
                               | new_listings_count  |
                               | sold_count          |
                               | price_per_sqft      |
                               | sale_to_list_ratio  |
                               | price_change_yoy    |
                               | rent_change_yoy     |
                               | vacancy_rate        |
                               | population          |
                               | median_income       |
                               | unemployment_rate   |
                               | market_score        |
                               | trend_direction     |
                               | ai_insights (JSONB) |
                               | data_source         |
                               | created_at          |
                               | updated_at          |
                               +---------------------+
```

### Relationships

| Relationship | Type | FK | ON DELETE |
|-------------|------|-----|----------|
| users -> saved_deals | 1:N | `saved_deals.user_id` | CASCADE |
| properties -> saved_deals | 1:N | `saved_deals.property_id` | CASCADE |
| users -> alerts | 1:N | `alerts.user_id` | CASCADE |

---

## Table Definitions

### `users`

Stores registered user accounts, authentication data, and subscription info.

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | PRIMARY KEY |
| `email` | VARCHAR(255) | No | - | UNIQUE |
| `hashed_password` | VARCHAR(255) | No | - | bcrypt hash |
| `full_name` | VARCHAR(255) | Yes | NULL | - |
| `phone` | VARCHAR(20) | Yes | NULL | E.164 format |
| `subscription_tier` | ENUM | No | `'free'` | free, starter, pro, enterprise |
| `stripe_customer_id` | VARCHAR(255) | Yes | NULL | UNIQUE |
| `stripe_subscription_id` | VARCHAR(255) | Yes | NULL | - |
| `is_active` | BOOLEAN | No | `true` | - |
| `is_verified` | BOOLEAN | No | `false` | Email verified flag |
| `is_superuser` | BOOLEAN | No | `false` | Admin flag |
| `last_login_at` | TIMESTAMPTZ | Yes | NULL | - |
| `created_at` | TIMESTAMPTZ | No | `now()` | Auto-set |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Auto-updated via trigger |

**Estimated row count**: 10K-100K
**Growth rate**: ~500-2,000 rows/month

---

### `properties`

Core table storing all scraped property listings with financial and AI analysis data.

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | PRIMARY KEY |
| `address_line1` | VARCHAR(500) | No | - | - |
| `address_line2` | VARCHAR(255) | Yes | NULL | - |
| `city` | VARCHAR(255) | No | - | - |
| `state` | VARCHAR(2) | No | - | 2-letter code |
| `zip_code` | VARCHAR(10) | No | - | - |
| `county` | VARCHAR(255) | Yes | NULL | - |
| `latitude` | NUMERIC(10,7) | Yes | NULL | - |
| `longitude` | NUMERIC(10,7) | Yes | NULL | - |
| `location` | GEOGRAPHY(Point, 4326) | Yes | NULL | Auto-set via trigger from lat/lng |
| `property_type` | ENUM | No | - | single_family, multi_family, condo, townhouse, land, commercial, mixed_use, mobile_home, other |
| `listing_status` | ENUM | No | `'active'` | active, pending, sold, off_market, foreclosure, auction, withdrawn |
| `listing_source` | ENUM | No | - | zillow, redfin, realtor, mls, public_records, auction, fsbo, other |
| `mls_number` | VARCHAR(50) | Yes | NULL | UNIQUE |
| `listing_url` | TEXT | Yes | NULL | - |
| `list_price` | NUMERIC(14,2) | Yes | NULL | - |
| `estimated_value` | NUMERIC(14,2) | Yes | NULL | AI/Zestimate/Redfin estimate |
| `last_sold_price` | NUMERIC(14,2) | Yes | NULL | - |
| `last_sold_date` | DATE | Yes | NULL | - |
| `estimated_rent` | NUMERIC(10,2) | Yes | NULL | Rentometer or model estimate |
| `hoa_fee` | NUMERIC(10,2) | Yes | NULL | Monthly |
| `tax_annual` | NUMERIC(10,2) | Yes | NULL | Annual property tax |
| `insurance_annual` | NUMERIC(10,2) | Yes | NULL | Annual insurance estimate |
| `bedrooms` | SMALLINT | Yes | NULL | - |
| `bathrooms` | NUMERIC(4,1) | Yes | NULL | Supports 2.5, etc. |
| `sqft` | INTEGER | Yes | NULL | Living area |
| `lot_sqft` | INTEGER | Yes | NULL | Lot area |
| `year_built` | SMALLINT | Yes | NULL | - |
| `stories` | SMALLINT | Yes | NULL | - |
| `units` | SMALLINT | Yes | `1` | Number of units (multi-family) |
| `parking_spaces` | SMALLINT | Yes | NULL | - |
| `description` | TEXT | Yes | NULL | Listing description |
| `photos` | JSONB | Yes | `'[]'` | Array of photo URLs |
| `investment_score` | NUMERIC(5,2) | Yes | NULL | 0.00-100.00 |
| `cap_rate` | NUMERIC(6,3) | Yes | NULL | Percentage as decimal |
| `cash_on_cash` | NUMERIC(6,3) | Yes | NULL | Percentage as decimal |
| `gross_yield` | NUMERIC(6,3) | Yes | NULL | Percentage as decimal |
| `price_per_sqft` | NUMERIC(10,2) | Yes | NULL | - |
| `rent_to_price_ratio` | NUMERIC(8,5) | Yes | NULL | - |
| `ai_summary` | TEXT | Yes | NULL | LLM-generated summary |
| `ai_analysis` | JSONB | Yes | NULL | Structured AI analysis |
| `raw_data` | JSONB | Yes | NULL | Original scraped data for debugging |
| `data_quality_score` | NUMERIC(5,2) | Yes | NULL | Completeness metric 0-100 |
| `last_scraped_at` | TIMESTAMPTZ | Yes | NULL | - |
| `listed_at` | TIMESTAMPTZ | Yes | NULL | Date originally listed |
| `created_at` | TIMESTAMPTZ | No | `now()` | - |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Auto-updated via trigger |

**Estimated row count**: 100K-10M
**Growth rate**: ~5,000-50,000 rows/day (varies by scraping scope)

---

### `saved_deals`

Junction table linking users to properties they have saved, with user-specific metadata.

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | PRIMARY KEY |
| `user_id` | UUID | No | - | FK -> users.id, ON DELETE CASCADE |
| `property_id` | UUID | No | - | FK -> properties.id, ON DELETE CASCADE |
| `notes` | TEXT | Yes | NULL | User notes |
| `custom_label` | VARCHAR(100) | Yes | NULL | e.g., "house_hack", "brrrr" |
| `is_favorite` | BOOLEAN | No | `false` | - |
| `custom_analysis` | JSONB | Yes | NULL | User's own numbers |
| `offer_price` | NUMERIC(14,2) | Yes | NULL | User's intended offer |
| `created_at` | TIMESTAMPTZ | No | `now()` | - |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Auto-updated via trigger |

**Constraints**: UNIQUE on (`user_id`, `property_id`)
**Estimated row count**: 10K-500K
**Growth rate**: ~1,000-10,000 rows/month

---

### `alerts`

Stores user-configured alert criteria and delivery preferences.

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | PRIMARY KEY |
| `user_id` | UUID | No | - | FK -> users.id, ON DELETE CASCADE |
| `name` | VARCHAR(255) | No | - | - |
| `is_active` | BOOLEAN | No | `true` | - |
| `channel` | ENUM | No | `'email'` | email, sms, push, webhook |
| `criteria` | JSONB | No | `'{}'` | Filter criteria (see API docs) |
| `frequency` | VARCHAR(50) | No | `'instant'` | instant, daily, weekly |
| `last_triggered_at` | TIMESTAMPTZ | Yes | NULL | - |
| `trigger_count` | INTEGER | No | `0` | - |
| `created_at` | TIMESTAMPTZ | No | `now()` | - |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Auto-updated via trigger |

**Estimated row count**: 5K-50K
**Growth rate**: ~500-2,000 rows/month

---

### `market_data`

Time-series market statistics aggregated by ZIP code and time period.

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | PRIMARY KEY |
| `zip_code` | VARCHAR(10) | No | - | - |
| `city` | VARCHAR(255) | Yes | NULL | - |
| `state` | VARCHAR(2) | No | - | - |
| `county` | VARCHAR(255) | Yes | NULL | - |
| `period_start` | DATE | No | - | - |
| `period_end` | DATE | No | - | - |
| `median_list_price` | NUMERIC(14,2) | Yes | NULL | - |
| `median_sold_price` | NUMERIC(14,2) | Yes | NULL | - |
| `median_rent` | NUMERIC(10,2) | Yes | NULL | - |
| `median_dom` | INTEGER | Yes | NULL | Days on market |
| `inventory_count` | INTEGER | Yes | NULL | Active listings |
| `new_listings_count` | INTEGER | Yes | NULL | - |
| `sold_count` | INTEGER | Yes | NULL | - |
| `price_per_sqft` | NUMERIC(10,2) | Yes | NULL | Median |
| `sale_to_list_ratio` | NUMERIC(6,4) | Yes | NULL | e.g., 0.9650 |
| `price_change_yoy` | NUMERIC(6,3) | Yes | NULL | Year-over-year % |
| `rent_change_yoy` | NUMERIC(6,3) | Yes | NULL | Year-over-year % |
| `vacancy_rate` | NUMERIC(5,3) | Yes | NULL | e.g., 0.054 |
| `population` | INTEGER | Yes | NULL | - |
| `median_income` | NUMERIC(12,2) | Yes | NULL | - |
| `unemployment_rate` | NUMERIC(5,3) | Yes | NULL | - |
| `market_score` | NUMERIC(5,2) | Yes | NULL | 0-100 |
| `trend_direction` | VARCHAR(20) | Yes | NULL | appreciating, stable, declining |
| `ai_insights` | JSONB | Yes | NULL | AI-generated market analysis |
| `data_source` | VARCHAR(100) | Yes | NULL | - |
| `created_at` | TIMESTAMPTZ | No | `now()` | - |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Auto-updated via trigger |

**Constraints**: UNIQUE on (`zip_code`, `period_start`, `period_end`)
**Estimated row count**: 500K-5M (41K ZIP codes x ~12-120 periods)
**Growth rate**: ~41,000 rows/month (monthly snapshots per ZIP)

---

## Index Strategy

### Properties Table — Primary Indexes

| Index Name | Column(s) | Type | Purpose |
|-----------|-----------|------|---------|
| `ix_properties_zip_code` | `zip_code` | B-tree | ZIP code filter (most common query) |
| `ix_properties_state_city` | `state, city` | B-tree | Geographic filter |
| `ix_properties_investment_score` | `investment_score` | B-tree | Sort by score |
| `ix_properties_cap_rate` | `cap_rate` | B-tree | Sort/filter by cap rate |
| `ix_properties_list_price` | `list_price` | B-tree | Price range filter |
| `ix_properties_listing_source` | `listing_source` | B-tree | Source filter |
| `ix_properties_listing_status` | `listing_status` | B-tree | Status filter |
| `ix_properties_property_type` | `property_type` | B-tree | Type filter |
| `ix_properties_mls_number` | `mls_number` | B-tree (unique) | Deduplication lookup |
| `ix_properties_listed_at` | `listed_at` | B-tree | Recency sort/filter |

### Properties Table — Specialized Indexes

| Index Name | Column(s) | Type | Purpose |
|-----------|-----------|------|---------|
| `ix_properties_location_gist` | `location` | GiST | Geospatial radius queries (`ST_DWithin`) |
| `ix_properties_address_trgm` | `address_line1` | GIN (gin_trgm_ops) | Fuzzy address matching for dedup |
| `ix_properties_state_score` | `state, investment_score DESC` | B-tree (composite) | State leaderboard queries |

### Other Tables

| Table | Index Name | Column(s) | Type | Purpose |
|-------|-----------|-----------|------|---------|
| users | `ix_users_email` | `email` | B-tree (unique) | Login lookup |
| users | `ix_users_subscription_tier` | `subscription_tier` | B-tree | Tier-based queries |
| users | `ix_users_stripe_customer_id` | `stripe_customer_id` | B-tree (unique) | Webhook lookup |
| saved_deals | `ix_saved_deals_user_id` | `user_id` | B-tree | User's deals list |
| saved_deals | `ix_saved_deals_property_id` | `property_id` | B-tree | Property's save count |
| saved_deals | `uq_saved_deals_user_property` | `user_id, property_id` | Unique | Prevent duplicates |
| alerts | `ix_alerts_user_id` | `user_id` | B-tree | User's alerts list |
| alerts | `ix_alerts_is_active` | `is_active` | B-tree | Active alert scan |
| alerts | `ix_alerts_criteria_gin` | `criteria` | GIN | JSONB containment queries |
| market_data | `ix_market_data_zip_code` | `zip_code` | B-tree | ZIP lookup |
| market_data | `ix_market_data_state_city` | `state, city` | B-tree | City-level aggregation |
| market_data | `ix_market_data_period` | `period_start, period_end` | B-tree | Time range queries |
| market_data | `uq_market_data_zip_period` | `zip_code, period_start, period_end` | Unique | Prevent duplicate snapshots |

### Index Design Rationale

1. **GiST for geography**: The `location` column uses PostGIS `geography(Point, 4326)` type. GiST index enables efficient `ST_DWithin(location, point, meters)` queries for "properties within X miles" searches. This is orders of magnitude faster than calculating distances on every row.

2. **GIN with trigram ops**: The `address_line1` trigram index supports `similarity()` and `%` operator queries used in the deduplication pipeline to find near-duplicate addresses (e.g., "123 Main St" vs "123 Main Street").

3. **GIN on JSONB criteria**: Enables efficient `@>` containment queries when matching new properties against alert criteria. For example: `WHERE criteria @> '{"states": ["TX"]}'::jsonb`.

4. **Composite indexes**: `(state, investment_score DESC)` supports the common query pattern "best deals in Texas sorted by score" without requiring a separate sort step.

---

## Query Patterns and Optimization

### Pattern 1: Property Search with Filters

```sql
-- Most common query: filtered property search
SELECT * FROM properties
WHERE state = 'TX'
  AND listing_status = 'active'
  AND list_price BETWEEN 200000 AND 400000
  AND property_type = 'single_family'
  AND bedrooms >= 3
ORDER BY investment_score DESC NULLS LAST
LIMIT 20 OFFSET 0;
```

**Optimization**: Uses `ix_properties_state_city` or `ix_properties_state_score` composite index. PostgreSQL's query planner will choose the best index based on selectivity.

### Pattern 2: Radius Search

```sql
-- Properties within 10 miles of a point
SELECT *, ST_Distance(location, ST_MakePoint(-97.7431, 30.2672)::geography) AS distance
FROM properties
WHERE ST_DWithin(location, ST_MakePoint(-97.7431, 30.2672)::geography, 16093)  -- 10 miles in meters
  AND listing_status = 'active'
ORDER BY distance ASC
LIMIT 20;
```

**Optimization**: GiST index on `location` column enables spatial index scan. The `ST_DWithin` function uses the index to quickly identify candidate rows.

### Pattern 3: Alert Matching

```sql
-- Find alerts matching a new property
SELECT a.* FROM alerts a
WHERE a.is_active = true
  AND (a.criteria->>'states' IS NULL OR a.criteria->'states' ? 'TX')
  AND (a.criteria->>'property_types' IS NULL OR a.criteria->'property_types' ? 'single_family')
  AND (a.criteria->>'min_price' IS NULL OR (a.criteria->>'min_price')::numeric <= 325000)
  AND (a.criteria->>'max_price' IS NULL OR (a.criteria->>'max_price')::numeric >= 325000)
  AND (a.criteria->>'min_investment_score' IS NULL OR (a.criteria->>'min_investment_score')::numeric <= 82.5);
```

**Optimization**: GIN index on `criteria` JSONB column. For high-volume alert matching, consider pre-materializing alert criteria into a separate indexed table.

### Pattern 4: Deduplication Check

```sql
-- Check for duplicate by MLS number (exact)
SELECT id FROM properties WHERE mls_number = 'MLS-2026-12345';

-- Check for duplicate by address (fuzzy)
SELECT id, address_line1, similarity(address_line1, '1234 Oak Street') AS sim
FROM properties
WHERE state = 'TX' AND zip_code = '78701'
  AND address_line1 % '1234 Oak Street'  -- trigram similarity > 0.3
ORDER BY sim DESC
LIMIT 5;
```

**Optimization**: MLS lookup uses the unique B-tree index. Address fuzzy match uses GIN trigram index with a `state + zip_code` pre-filter to narrow the search space.

### Pattern 5: Market Data Trends

```sql
-- Monthly trend for a ZIP code over the past year
SELECT period_start, median_list_price, median_rent, price_change_yoy
FROM market_data
WHERE zip_code = '78701'
  AND period_start >= '2025-03-01'
  AND period_end <= '2026-03-31'
ORDER BY period_start ASC;
```

**Optimization**: Composite index on `(zip_code, period_start, period_end)` covers this query entirely (index-only scan if selecting indexed columns).

---

## Database Triggers

### Auto-update `updated_at`

A trigger function automatically updates the `updated_at` column to `now()` on every `UPDATE` statement across all tables.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

Applied to: `users`, `properties`, `saved_deals`, `alerts`, `market_data`

### Auto-populate `location` from lat/lng

When `latitude` or `longitude` is inserted or updated on `properties`, a trigger automatically computes the PostGIS `geography` point.

```sql
CREATE OR REPLACE FUNCTION update_property_location()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Data Retention Policy

| Data Type | Retention | Action |
|-----------|-----------|--------|
| Active listings | Indefinite | Kept as long as listing_status is active |
| Sold/withdrawn listings | 2 years | Archived to cold storage (S3), removed from main table |
| Market data | 5 years | Kept for trend analysis, older data aggregated to quarterly |
| User accounts (active) | Indefinite | - |
| User accounts (inactive 1yr+) | Flagged | Soft-delete warning email, hard delete after 30 days |
| Raw scraped data (`raw_data` JSONB) | 90 days | Nullified after analysis is complete |
| Celery task results | 7 days | Auto-expired in Redis |
| API rate limit counters | 24 hours | Auto-expired in Redis |
| Session data | 7 days | Auto-expired in Redis |

### Archival Strategy

For the `properties` table, which will grow the fastest:

1. **Partition by listing_status**: Active properties in a hot partition, sold/archived in cold partitions
2. **Monthly archival job**: Move `sold` properties older than 2 years to an `properties_archive` table (or S3 Parquet files)
3. **VACUUM strategy**: Aggressive autovacuum on `properties` table due to frequent updates:
   ```
   ALTER TABLE properties SET (autovacuum_vacuum_scale_factor = 0.05);
   ALTER TABLE properties SET (autovacuum_analyze_scale_factor = 0.02);
   ```

### Backup Strategy

| Backup Type | Frequency | Retention | Method |
|-------------|-----------|-----------|--------|
| Full backup | Daily | 30 days | pg_dump to S3 with encryption |
| WAL archiving | Continuous | 7 days | Streaming replication / WAL-G |
| Point-in-time | On demand | 7 days | WAL replay |
| Logical backup | Weekly | 90 days | pg_dump --format=custom |
