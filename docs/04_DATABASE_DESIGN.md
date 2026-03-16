# RealDeal AI — Database Design

---

## 1. ER Diagram (Simplified)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  landlords   │────<│  properties  │────<│    units     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                           ┌──────┴───────┐
                                           │   leases     │
                                           └──────┬───────┘
                                                  │
                                           ┌──────┴───────┐
                                           │   tenants    │
                                           └──┬───┬───┬───┘
                                              │   │   │
                              ┌───────────────┘   │   └────────────────┐
                              │                   │                    │
                     ┌────────▼──────┐  ┌─────────▼────────┐  ┌───────▼────────┐
                     │  payments     │  │  maintenance_    │  │  conversations │
                     │               │  │  requests        │  │                │
                     └───────────────┘  └────────┬─────────┘  └───────┬────────┘
                                                 │                    │
                                        ┌────────▼─────────┐  ┌──────▼────────┐
                                        │  quotes          │  │  messages     │
                                        └────────┬─────────┘  └───────────────┘
                                                 │
                                        ┌────────▼─────────┐
                                        │  contractors     │
                                        └──────────────────┘
```

---

## 2. Full Schema (PostgreSQL)

### Core Tables

```sql
-- ============================================================
-- LANDLORDS (Account holders)
-- ============================================================
CREATE TABLE landlords (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    phone           VARCHAR(20),
    company_name    VARCHAR(200),
    stripe_account_id VARCHAR(100),       -- Stripe Connect
    plan_tier       VARCHAR(20) DEFAULT 'starter',  -- starter | growth | pro
    settings        JSONB DEFAULT '{}',   -- AI preferences, thresholds
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PROPERTIES
-- ============================================================
CREATE TABLE properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    landlord_id     UUID NOT NULL REFERENCES landlords(id),
    name            VARCHAR(200) NOT NULL,       -- "Maple Street Apartments"
    address_line1   VARCHAR(255) NOT NULL,
    address_line2   VARCHAR(255),
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(2) NOT NULL,
    zip_code        VARCHAR(10) NOT NULL,
    property_type   VARCHAR(20) NOT NULL,        -- sfh | multi | condo | townhouse
    total_units     INTEGER NOT NULL DEFAULT 1,
    purchase_price  DECIMAL(12,2),
    current_value   DECIMAL(12,2),
    mortgage_payment DECIMAL(10,2),
    insurance_cost  DECIMAL(10,2),
    tax_annual      DECIMAL(10,2),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_properties_landlord ON properties(landlord_id);

-- ============================================================
-- UNITS
-- ============================================================
CREATE TABLE units (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID NOT NULL REFERENCES properties(id),
    unit_number     VARCHAR(20) NOT NULL,
    bedrooms        SMALLINT,
    bathrooms       DECIMAL(3,1),
    sqft            INTEGER,
    market_rent     DECIMAL(10,2),
    status          VARCHAR(20) DEFAULT 'vacant', -- vacant | occupied | maintenance | turnover
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(property_id, unit_number)
);

CREATE INDEX idx_units_property ON units(property_id);

-- ============================================================
-- TENANTS
-- ============================================================
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    landlord_id     UUID NOT NULL REFERENCES landlords(id),
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255),
    phone           VARCHAR(20) NOT NULL,
    password_hash   VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    portal_enabled  BOOLEAN DEFAULT FALSE,
    preferred_language VARCHAR(5) DEFAULT 'en',
    stripe_customer_id VARCHAR(100),
    plaid_access_token VARCHAR(255),       -- encrypted
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_landlord ON tenants(landlord_id);
CREATE INDEX idx_tenants_phone ON tenants(phone);

-- ============================================================
-- LEASES
-- ============================================================
CREATE TABLE leases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id         UUID NOT NULL REFERENCES units(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    rent_amount     DECIMAL(10,2) NOT NULL,
    deposit_amount  DECIMAL(10,2),
    start_date      DATE NOT NULL,
    end_date        DATE,                        -- NULL = month-to-month
    rent_due_day    SMALLINT DEFAULT 1,          -- Day of month
    late_fee_amount DECIMAL(10,2),
    late_fee_grace_days SMALLINT DEFAULT 5,
    lease_type      VARCHAR(20) DEFAULT 'fixed', -- fixed | month_to_month
    status          VARCHAR(20) DEFAULT 'active', -- active | expired | terminated
    document_id     UUID REFERENCES documents(id),
    ai_analysis     JSONB,                       -- Parsed lease terms
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_leases_unit ON leases(unit_id);
CREATE INDEX idx_leases_tenant ON leases(tenant_id);
CREATE INDEX idx_leases_status ON leases(status);
```

### Financial Tables

```sql
-- ============================================================
-- PAYMENTS
-- ============================================================
CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id        UUID NOT NULL REFERENCES leases(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    amount          DECIMAL(10,2) NOT NULL,
    payment_type    VARCHAR(20) NOT NULL,         -- rent | late_fee | deposit | other
    payment_method  VARCHAR(20),                  -- stripe | ach | zelle | cash | check
    status          VARCHAR(20) DEFAULT 'pending', -- pending | completed | failed | refunded
    stripe_payment_id VARCHAR(100),
    due_date        DATE NOT NULL,
    paid_date       TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_lease ON payments(lease_id);
CREATE INDEX idx_payments_tenant ON payments(tenant_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_due_date ON payments(due_date);

-- ============================================================
-- EXPENSES
-- ============================================================
CREATE TABLE expenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID NOT NULL REFERENCES properties(id),
    unit_id         UUID REFERENCES units(id),     -- NULL = property-wide
    maintenance_request_id UUID REFERENCES maintenance_requests(id),
    category        VARCHAR(50) NOT NULL,           -- maintenance | insurance | tax | utility | management | other
    description     TEXT NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    vendor_name     VARCHAR(200),
    expense_date    DATE NOT NULL,
    receipt_doc_id  UUID REFERENCES documents(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_expenses_property ON expenses(property_id);
CREATE INDEX idx_expenses_date ON expenses(expense_date);
CREATE INDEX idx_expenses_category ON expenses(category);
```

### Maintenance Tables

```sql
-- ============================================================
-- MAINTENANCE REQUESTS
-- ============================================================
CREATE TABLE maintenance_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id         UUID NOT NULL REFERENCES units(id),
    tenant_id       UUID REFERENCES tenants(id),
    landlord_id     UUID NOT NULL REFERENCES landlords(id),
    title           VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    category        VARCHAR(50),                  -- plumbing | electrical | hvac | appliance | structural | pest | other
    urgency         VARCHAR(20) DEFAULT 'routine', -- emergency | urgent | routine
    status          VARCHAR(20) DEFAULT 'new',     -- new | diagnosed | quoting | approved | scheduled | in_progress | completed | cancelled
    ai_diagnosis    JSONB,                         -- Vision model output
    ai_confidence   DECIMAL(3,2),
    estimated_cost_low  DECIMAL(10,2),
    estimated_cost_high DECIMAL(10,2),
    actual_cost     DECIMAL(10,2),
    scheduled_date  TIMESTAMPTZ,
    completed_date  TIMESTAMPTZ,
    tenant_rating   SMALLINT,                      -- 1-5
    tenant_feedback TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_maint_unit ON maintenance_requests(unit_id);
CREATE INDEX idx_maint_landlord ON maintenance_requests(landlord_id);
CREATE INDEX idx_maint_status ON maintenance_requests(status);
CREATE INDEX idx_maint_urgency ON maintenance_requests(urgency);

-- ============================================================
-- MAINTENANCE PHOTOS
-- ============================================================
CREATE TABLE maintenance_photos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES maintenance_requests(id),
    s3_key          VARCHAR(500) NOT NULL,
    ai_analysis     JSONB,
    uploaded_by     VARCHAR(20) NOT NULL,          -- tenant | landlord | contractor
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CONTRACTORS
-- ============================================================
CREATE TABLE contractors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    landlord_id     UUID NOT NULL REFERENCES landlords(id),
    company_name    VARCHAR(200) NOT NULL,
    contact_name    VARCHAR(200),
    phone           VARCHAR(20) NOT NULL,
    email           VARCHAR(255),
    trades          VARCHAR(50)[] NOT NULL,        -- ARRAY: plumbing, electrical, etc.
    service_area_zips VARCHAR(10)[],
    avg_rating      DECIMAL(3,2) DEFAULT 0,
    total_jobs      INTEGER DEFAULT 0,
    avg_response_hours DECIMAL(5,1),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contractors_landlord ON contractors(landlord_id);
CREATE INDEX idx_contractors_trades ON contractors USING GIN(trades);

-- ============================================================
-- QUOTES
-- ============================================================
CREATE TABLE quotes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES maintenance_requests(id),
    contractor_id   UUID NOT NULL REFERENCES contractors(id),
    amount          DECIMAL(10,2) NOT NULL,
    description     TEXT,
    estimated_hours DECIMAL(5,1),
    available_date  TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'pending', -- pending | accepted | rejected | expired
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quotes_request ON quotes(request_id);
```

### Communication Tables

```sql
-- ============================================================
-- CONVERSATIONS
-- ============================================================
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    landlord_id     UUID NOT NULL REFERENCES landlords(id),
    channel         VARCHAR(20) NOT NULL,          -- sms | email | web | whatsapp
    status          VARCHAR(20) DEFAULT 'active',  -- active | escalated | resolved
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_tenant ON conversations(tenant_id);

-- ============================================================
-- MESSAGES
-- ============================================================
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    sender_type     VARCHAR(20) NOT NULL,          -- tenant | ai | landlord
    content         TEXT NOT NULL,
    intent          VARCHAR(50),                   -- maintenance | payment | lease | general
    confidence      DECIMAL(3,2),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_type  VARCHAR(20) NOT NULL,          -- landlord | tenant
    recipient_id    UUID NOT NULL,
    title           VARCHAR(200) NOT NULL,
    body            TEXT NOT NULL,
    category        VARCHAR(50),                   -- payment | maintenance | lease | system
    is_read         BOOLEAN DEFAULT FALSE,
    action_url      VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_type, recipient_id);
CREATE INDEX idx_notifications_unread ON notifications(recipient_id) WHERE is_read = FALSE;
```

### Document Tables

```sql
-- ============================================================
-- DOCUMENTS
-- ============================================================
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    landlord_id     UUID NOT NULL REFERENCES landlords(id),
    property_id     UUID REFERENCES properties(id),
    unit_id         UUID REFERENCES units(id),
    tenant_id       UUID REFERENCES tenants(id),
    doc_type        VARCHAR(50) NOT NULL,          -- lease | inspection | contract | notice | receipt | insurance | other
    filename        VARCHAR(255) NOT NULL,
    s3_key          VARCHAR(500) NOT NULL,
    file_size       INTEGER,
    mime_type       VARCHAR(100),
    ai_analysis     JSONB,                         -- Lease analyzer output
    ocr_text        TEXT,
    tags            VARCHAR(50)[],
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_landlord ON documents(landlord_id);
CREATE INDEX idx_documents_property ON documents(property_id);
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
```

---

## 3. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| UUIDs for PKs | Safe for distributed systems, no sequential ID leakage |
| JSONB for AI outputs | Schema flexibility as AI models evolve |
| Soft deletes | Audit trail, regulatory compliance |
| Array columns for trades/tags | PostgreSQL native, avoids join tables for simple lists |
| Separate expenses table | Decoupled from maintenance for manual expense entry |
| TIMESTAMPTZ everywhere | Timezone-safe across all regions |
| Row-level security via `landlord_id` | Every tenant-facing query filtered by landlord context |

---

## 4. Indexes Strategy

- **Foreign keys**: All indexed for JOIN performance
- **Status columns**: Partial indexes on active statuses for dashboard queries
- **Date columns**: For financial reporting range queries
- **GIN indexes**: For array columns (trades, tags) and JSONB queries
- **Composite indexes** added as query patterns emerge in production
