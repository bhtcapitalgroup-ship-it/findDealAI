# RealDeal AI — API Architecture

---

## 1. System Architecture Overview

```
                    ┌──────────────────┐
                    │   CloudFront     │
                    │   CDN + WAF      │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │  React SPA      │          │  Tenant Portal  │
     │  (Landlord)     │          │  (Tenant)       │
     └────────┬────────┘          └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             │ HTTPS
                    ┌────────▼────────┐
                    │  API Gateway    │
                    │  (Kong / AWS)   │
                    │  Rate Limiting  │
                    │  Auth (JWT)     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼───────┐  ┌───────▼────────┐  ┌───────▼───────┐
│  Core API      │  │  AI Service    │  │  Comms Service│
│  (FastAPI)     │  │  (FastAPI)     │  │  (FastAPI)    │
│                │  │                │  │               │
│ • Auth         │  │ • Chat Agent   │  │ • Twilio SMS  │
│ • Properties   │  │ • Vision       │  │ • SendGrid    │
│ • Units        │  │ • Lease Parse  │  │ • WebSocket   │
│ • Tenants      │  │ • Diagnosis    │  │ • WhatsApp    │
│ • Maintenance  │  │ • Classification│ │               │
│ • Payments     │  │                │  │               │
│ • Documents    │  │                │  │               │
│ • Financials   │  │                │  │               │
└───────┬────────┘  └───────┬────────┘  └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
     ┌────────▼───┐  ┌─────▼─────┐  ┌────▼──────┐
     │ PostgreSQL │  │  Redis    │  │  AWS S3   │
     │ (RDS)      │  │ (Cache +  │  │ (Files)   │
     │            │  │  Queues)  │  │           │
     └────────────┘  └───────────┘  └───────────┘
```

---

## 2. Service Decomposition

### Core API (Port 8000)
The primary CRUD service. Handles all business logic.

### AI Service (Port 8001)
Stateless AI inference service. Horizontally scalable.

### Communications Service (Port 8002)
Handles all external messaging. Manages channel adapters and delivery.

### Background Workers (Celery + Redis)
- Payment reminder scheduler
- Contractor outreach automation
- Report generation
- Document processing (OCR pipeline)

---

## 3. API Endpoints

### 3.1 Authentication

```
POST   /api/v1/auth/register          # Landlord registration
POST   /api/v1/auth/login             # JWT token pair
POST   /api/v1/auth/refresh           # Refresh access token
POST   /api/v1/auth/tenant/verify     # Tenant OTP verification
POST   /api/v1/auth/forgot-password   # Password reset request
POST   /api/v1/auth/reset-password    # Password reset confirm
```

### 3.2 Properties

```
GET    /api/v1/properties                     # List landlord's properties
POST   /api/v1/properties                     # Create property
GET    /api/v1/properties/{id}                # Get property detail
PUT    /api/v1/properties/{id}                # Update property
DELETE /api/v1/properties/{id}                # Soft delete
GET    /api/v1/properties/{id}/financials     # Property financial summary
POST   /api/v1/properties/import              # Bulk import from CSV
```

### 3.3 Units

```
GET    /api/v1/properties/{id}/units          # List units for property
POST   /api/v1/properties/{id}/units          # Create unit
GET    /api/v1/units/{id}                     # Unit detail
PUT    /api/v1/units/{id}                     # Update unit
GET    /api/v1/units/{id}/history             # Tenant + maintenance history
```

### 3.4 Tenants

```
GET    /api/v1/tenants                        # List all tenants
POST   /api/v1/tenants                        # Create + invite tenant
GET    /api/v1/tenants/{id}                   # Tenant detail
PUT    /api/v1/tenants/{id}                   # Update tenant
POST   /api/v1/tenants/{id}/invite            # Re-send invite
GET    /api/v1/tenants/{id}/payments          # Tenant payment history
GET    /api/v1/tenants/{id}/requests          # Tenant maintenance requests
```

### 3.5 Maintenance

```
GET    /api/v1/maintenance                    # List requests (filterable)
POST   /api/v1/maintenance                    # Create request
GET    /api/v1/maintenance/{id}               # Request detail
PUT    /api/v1/maintenance/{id}               # Update request
POST   /api/v1/maintenance/{id}/diagnose      # AI photo diagnosis
POST   /api/v1/maintenance/{id}/quotes        # Request contractor quotes
POST   /api/v1/maintenance/{id}/approve       # Approve a quote
POST   /api/v1/maintenance/{id}/complete      # Mark complete
POST   /api/v1/maintenance/{id}/feedback      # Tenant/landlord feedback

GET    /api/v1/contractors                    # List contractors
POST   /api/v1/contractors                    # Add contractor
PUT    /api/v1/contractors/{id}               # Update contractor
GET    /api/v1/contractors/{id}/reviews       # Contractor reviews
```

### 3.6 Payments

```
GET    /api/v1/payments                       # List all payments
POST   /api/v1/payments/charge                # Initiate payment
GET    /api/v1/payments/{id}                  # Payment detail
POST   /api/v1/payments/setup-ach             # Plaid ACH setup
POST   /api/v1/payments/confirm-zelle         # Manual Zelle confirmation
GET    /api/v1/payments/aging                 # Aging report
GET    /api/v1/payments/summary               # Collection summary

POST   /api/v1/stripe/webhook                # Stripe webhook handler
POST   /api/v1/plaid/webhook                 # Plaid webhook handler
```

### 3.7 Documents

```
GET    /api/v1/documents                      # List documents (filterable)
POST   /api/v1/documents/upload               # Upload document → S3
GET    /api/v1/documents/{id}                 # Document metadata
GET    /api/v1/documents/{id}/download        # Pre-signed S3 URL
DELETE /api/v1/documents/{id}                 # Soft delete
POST   /api/v1/documents/{id}/analyze         # AI lease analysis
```

### 3.8 AI / Chat

```
POST   /api/v1/ai/chat                       # Tenant chat message
GET    /api/v1/ai/conversations/{tenant_id}   # Conversation history
POST   /api/v1/ai/classify                   # Classify maintenance issue
POST   /api/v1/ai/diagnose                   # Vision-based diagnosis
POST   /api/v1/ai/lease/analyze              # Lease analysis
GET    /api/v1/ai/escalations                # Escalated items for landlord
POST   /api/v1/ai/escalations/{id}/resolve   # Resolve escalation
```

### 3.9 Financials

```
GET    /api/v1/financials/dashboard           # Portfolio overview
GET    /api/v1/financials/income              # Income breakdown
GET    /api/v1/financials/expenses            # Expense breakdown
GET    /api/v1/financials/noi                 # NOI calculation
GET    /api/v1/financials/cashflow            # Cash flow report
GET    /api/v1/financials/export              # CSV/PDF export
POST   /api/v1/financials/expenses            # Log manual expense
```

### 3.10 Webhooks (Inbound)

```
POST   /api/v1/webhooks/twilio               # Inbound SMS
POST   /api/v1/webhooks/sendgrid             # Inbound email
POST   /api/v1/webhooks/stripe               # Payment events
POST   /api/v1/webhooks/plaid                # ACH events
```

---

## 4. Authentication & Authorization

```
JWT Access Token (15 min TTL)
├── Landlord role
│   ├── Full CRUD on own properties, units, tenants
│   ├── Financial data access
│   ├── AI configuration
│   └── Document management
├── Tenant role
│   ├── Read own unit, lease info
│   ├── Create maintenance requests
│   ├── Make payments
│   ├── Chat with AI
│   └── View own documents
└── Contractor role (Phase 2)
    ├── View assigned work orders
    ├── Submit quotes
    └── Update job status
```

**Multi-tenancy:** All queries scoped by `landlord_id` at the ORM level.
Row-level security enforced via SQLAlchemy middleware.

---

## 5. Rate Limiting

| Endpoint Group | Limit |
|---------------|-------|
| Auth | 10 req/min |
| AI Chat | 30 req/min per tenant |
| AI Vision | 10 req/min per landlord |
| CRUD | 100 req/min |
| Webhooks | 500 req/min |
| File Upload | 20 req/min |

---

## 6. Async Processing (Celery Tasks)

```python
# Payment tasks
send_rent_reminder.delay(tenant_id)
process_late_fee.delay(lease_id)
generate_receipt.delay(payment_id)

# Maintenance tasks
contact_contractors.delay(request_id, contractor_ids)
follow_up_quote.delay(request_id)

# AI tasks
process_photo_diagnosis.delay(request_id, image_key)
analyze_lease_document.delay(document_id)
ocr_document.delay(document_id)

# Reporting tasks
generate_monthly_report.delay(landlord_id, month)
export_tax_report.delay(landlord_id, year)
```

---

## 7. External Integrations

| Service | Purpose | Integration Type |
|---------|---------|-----------------|
| Twilio | SMS send/receive | REST API + Webhooks |
| SendGrid | Email | REST API + Webhooks |
| Stripe | Card payments, payouts | SDK + Webhooks |
| Plaid | ACH bank linking | SDK + Webhooks |
| Anthropic Claude | LLM + Vision | REST API |
| AWS S3 | File storage | SDK |
| AWS SES | Transactional email (fallback) | SDK |
| Google Maps | Address validation | REST API |
