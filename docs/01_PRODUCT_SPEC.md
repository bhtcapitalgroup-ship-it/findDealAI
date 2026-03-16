# RealDeal AI — Product Specification
## AI-First Property Management for Small Landlords (5–50 Units)

---

## 1. Vision

Replace 80% of a landlord's daily work with AI agents. A landlord should be able to
manage 50 units with the same effort it currently takes to manage 5.

**Tagline:** _"Your AI property manager that never sleeps."_

---

## 2. Target User

| Attribute | Detail |
|-----------|--------|
| Portfolio | 5–50 residential units |
| Tech comfort | Uses smartphone, basic web apps |
| Pain points | Tenant calls, maintenance coordination, late rent, bookkeeping |
| Current tools | Spreadsheets, Venmo, paper leases, personal phone |

---

## 3. Core Modules

### 3.1 Tenant Communication AI ("TenantBot")

| Capability | Detail |
|------------|--------|
| Channels | SMS (Twilio), Email, In-app chat, WhatsApp |
| Inbound handling | Classify intent → route to correct workflow |
| Intents supported | Maintenance request, payment question, lease question, complaint, general inquiry |
| Escalation | Confidence < 0.7 or flagged keywords → notify landlord |
| Tone | Professional, empathetic, legally neutral |
| Languages | English, Spanish (MVP) |

**AI Pipeline:**
```
Tenant Message
  → Intent Classifier (LLM)
  → Entity Extraction (unit, issue type, urgency)
  → Route to Handler:
      ├── Maintenance → Maintenance Automation
      ├── Payment → Rent Collection Module
      ├── Lease → Lease Knowledge Base
      └── Escalation → Landlord Notification
  → Generate Response (LLM)
  → Send via Channel
```

### 3.2 Maintenance Automation

**Workflow:**
```
1. Tenant submits issue (text + optional photo)
2. AI categorizes: plumbing | electrical | HVAC | appliance | structural | pest | other
3. AI assigns urgency: emergency (≤4h) | urgent (≤24h) | routine (≤7d)
4. System matches contractor from approved vendor list
5. AI sends RFQ to top 3 contractors
6. Landlord approves quote (or auto-approve if < threshold)
7. Contractor scheduled, tenant notified
8. Post-repair: tenant confirms resolution
9. Invoice logged to financial dashboard
```

**Contractor Matching Criteria:**
- Trade specialty match
- Availability
- Historical rating (from landlord + tenant feedback)
- Price competitiveness
- Response time history

### 3.3 Rent Collection

| Feature | Detail |
|---------|--------|
| Payment methods | Stripe (card), ACH (Plaid), Zelle (manual confirm) |
| Auto-charge | Opt-in recurring ACH on due date |
| Reminders | 3 days before → due date → 1 day late → 3 days late → 7 days late |
| Late fees | Auto-calculate per lease terms |
| Partial payments | Accept and track balance |
| Receipts | Auto-generated, emailed |
| Reporting | Payment history per tenant, aging report |

**Reminder Escalation:**
```
Day -3:  SMS "Friendly reminder: rent of $X due on [date]"
Day  0:  SMS "Rent is due today. Pay here: [link]"
Day +1:  SMS + Email "Rent is 1 day past due."
Day +3:  SMS + Email + Landlord notified
Day +7:  Landlord gets recommended next steps (demand letter template)
```

### 3.4 AI Maintenance Diagnosis (Vision)

| Capability | Detail |
|------------|--------|
| Input | Photo or short video frame |
| Detection | Water damage, mold, cracks, HVAC issues, appliance damage, pest evidence |
| Output | Issue classification, severity (1-5), recommended action, estimated cost range |
| Model | Claude vision / fine-tuned model |
| Fallback | If confidence < 0.6, flag for landlord review |

**Example Flow:**
```
Tenant uploads photo of ceiling stain
  → Vision model: "Water damage — severity 3/5 — likely pipe leak above"
  → Recommendation: "Suggest plumber inspection within 24 hours"
  → Auto-creates maintenance ticket with category: plumbing, urgency: urgent
```

### 3.5 Financial Dashboard

**Metrics:**
| Metric | Calculation |
|--------|-------------|
| Gross Rental Income | Sum of all collected rent |
| Vacancy Loss | (Vacant units / Total units) × Market rent |
| Operating Expenses | Maintenance + Insurance + Tax + Management fees |
| NOI | Gross Income − Operating Expenses |
| Cash Flow | NOI − Debt Service |
| Cap Rate | NOI / Property Value |
| Expense Ratio | Operating Expenses / Gross Income |

**Views:**
- Portfolio overview (all properties)
- Per-property P&L
- Per-unit economics
- Monthly / Quarterly / Annual trends
- Tax-ready export (CSV, PDF)

### 3.6 Document Management

| Document Type | Features |
|---------------|----------|
| Leases | Upload, parse key dates, auto-remind on renewal |
| Inspection reports | Photo + notes, timestamped |
| Contracts | Vendor agreements, insurance policies |
| Notices | Late payment, lease violation, move-out |
| Receipts | Auto-filed from maintenance invoices |

**Storage:** AWS S3 with server-side encryption (AES-256)
**Organization:** Auto-tagged by property, unit, tenant, document type

### 3.7 AI Lease Analyzer

| Capability | Detail |
|------------|--------|
| Input | PDF or image of lease |
| OCR | Extract text from scanned documents |
| Analysis | Identify key clauses, dates, obligations |
| Risk flags | Unusual terms, missing standard clauses, unfavorable conditions |
| Output | Structured summary + risk score |

**Extracted Fields:**
- Lease term (start/end)
- Rent amount and due date
- Security deposit terms
- Late fee structure
- Maintenance responsibilities
- Termination clauses
- Renewal terms
- Pet policy
- Subletting policy

---

## 4. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Availability | 99.9% uptime |
| Response time | API < 200ms p95, AI < 3s p95 |
| Data residency | US (AWS us-east-1) |
| Compliance | Fair Housing Act (no discriminatory language in AI), state landlord-tenant laws |
| Security | SOC 2 Type II (target Year 2), encryption at rest + in transit |
| Mobile | Responsive web MVP, native app Phase 2 |
