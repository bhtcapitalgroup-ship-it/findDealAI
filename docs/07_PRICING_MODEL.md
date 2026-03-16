# RealDeal AI — Pricing Model

---

## Pricing Philosophy

- **Value-based:** Price against the cost of a human property manager (8-12% of rent)
- **Land and expand:** Free tier to capture small landlords, grow with their portfolio
- **AI as the moat:** AI features drive upgrades, not basic CRUD

---

## Tier Structure

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRICING TIERS                                    │
├──────────────┬──────────────────┬──────────────────┬────────────────────┤
│   STARTER    │     GROWTH       │       PRO        │    ENTERPRISE      │
│    Free      │   $2/unit/mo     │   $4/unit/mo     │     Custom         │
│  (≤5 units)  │   (6-25 units)   │  (26-100 units)  │   (100+ units)     │
├──────────────┼──────────────────┼──────────────────┼────────────────────┤
│              │                  │                  │                    │
│ ✓ Rent       │ ✓ Everything in  │ ✓ Everything in  │ ✓ Everything in    │
│   collection │   Starter        │   Growth         │   Pro              │
│ ✓ Basic      │ ✓ TenantBot AI   │ ✓ Vision         │ ✓ Dedicated        │
│   dashboard  │   (SMS + Web)    │   diagnostics    │   account mgr      │
│ ✓ Maintenance│ ✓ Auto rent      │ ✓ Lease analyzer │ ✓ Custom AI        │
│   tracking   │   reminders      │ ✓ Contractor     │   training         │
│ ✓ Document   │ ✓ Maintenance    │   auto-matching  │ ✓ API access       │
│   storage    │   AI classify    │ ✓ Financial      │ ✓ White-label      │
│   (1GB)      │ ✓ 5GB storage    │   reports + tax  │   option           │
│ ✓ 1 property │ ✓ Unlimited      │ ✓ 25GB storage   │ ✓ SLA guarantee    │
│              │   properties     │ ✓ Priority       │ ✓ Unlimited        │
│              │ ✓ Email support  │   support        │   storage          │
│              │                  │ ✓ WhatsApp       │ ✓ Phone support    │
│              │                  │ ✓ Multi-language  │                    │
└──────────────┴──────────────────┴──────────────────┴────────────────────┘
```

---

## Revenue Projections

### Unit Economics

| Metric | Value |
|--------|-------|
| Average units per paying customer | 18 |
| Blended ARPU | $54/month ($3/unit avg) |
| AI cost per unit | ~$0.08/month |
| Infrastructure cost per unit | ~$0.15/month |
| Payment processing margin | $0 (pass-through) |
| Gross margin per unit | ~$2.77/unit (92%) |
| CAC target | < $150 |
| LTV (24-month retention) | $1,296 |
| LTV:CAC ratio | > 8:1 |

### Revenue Ramp

| Month | Landlords | Total Units | MRR | ARR |
|-------|-----------|-------------|-----|-----|
| 3 (beta) | 10 | 180 | $540 | $6.5K |
| 6 (launch) | 50 | 900 | $2,700 | $32K |
| 12 | 200 | 3,600 | $10,800 | $130K |
| 18 | 500 | 9,000 | $27,000 | $324K |
| 24 | 1,200 | 21,600 | $64,800 | $778K |

---

## Payment Processing Revenue

| Method | Fee to Tenant | RealDeal Take | Notes |
|--------|--------------|---------------|-------|
| ACH | $1.50 flat | $0 | Pass-through (encourage adoption) |
| Credit card | 2.9% + $0.30 | 0.5% markup | Revenue on convenience |
| Zelle | Free | $0 | Manual confirmation |

**Card processing revenue at scale (1,200 landlords):**
~30% pay by card × 21,600 units × $1,500 avg rent × 0.5% = ~$48,600/month

---

## Competitive Positioning

```
                        AI Capability
                             ▲
                             │
                    RealDeal │ ★
                      AI     │
                             │
                             │
          ┌──────────────────┼──────────────────────┐
          │                  │                      │
          │   Avail          │          AppFolio    │
          │   TurboTenant    │          Buildium    │
          │   Rentec Direct  │                      │
          │                  │                      │
          │        Spreadsheets                     │
──────────┼──────────────────┼──────────────────────┼──────── Price
   Free   │                  │                      │  $$$
          │                  │                      │
          └──────────────────┴──────────────────────┘
```

| Competitor | Price | Units Target | AI Features |
|-----------|-------|-------------|-------------|
| AppFolio | $1.40/unit/mo ($280 min) | 50+ | Basic automation |
| Buildium | $55-175/mo flat | 20-5000 | None |
| TurboTenant | Free-$12/mo | 1-100 | None |
| Avail | Free-$7/unit/mo | 1-20 | None |
| **RealDeal AI** | **Free-$4/unit/mo** | **1-100** | **Full AI stack** |

**Advantage:** Only platform where AI handles tenant communication, diagnoses
maintenance from photos, and analyzes leases — at a price point accessible
to small landlords.

---

## Monetization Roadmap

| Phase | Revenue Stream | Timeline |
|-------|---------------|----------|
| Launch | SaaS subscriptions | Month 0 |
| Launch | Payment processing margin | Month 0 |
| Month 6 | Contractor marketplace (referral fees) | Month 6 |
| Month 12 | Tenant screening fees ($35/screen) | Month 12 |
| Month 12 | Insurance referrals (landlord + renter) | Month 12 |
| Month 18 | Premium AI add-ons (market rent analysis) | Month 18 |
| Month 24 | Data insights (anonymized market data) | Month 24 |

---

## Free Tier Strategy

The free tier (≤5 units) exists to:

1. **Capture solo landlords** who will grow into paying customers
2. **Generate word-of-mouth** in landlord communities
3. **Build data moat** — more conversations = better AI
4. **Reduce CAC** — organic growth from free users

**Conversion trigger:** When a landlord adds their 6th unit, they hit a
natural upgrade point. At this scale, $2/unit/month ($12/mo total) is a
trivial cost vs. the time saved.
