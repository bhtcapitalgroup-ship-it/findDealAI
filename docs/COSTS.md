# RealDeal AI — Cost Estimates and Financial Projections

## Infrastructure Costs

### AWS-Based Deployment (Primary Estimate)

#### Pre-Launch / Development (Months 1-2)

| Service | Spec | Monthly Cost |
|---------|------|-------------|
| EC2 (backend + workers) | 1x t3.xlarge (4 vCPU, 16 GB) | $120 |
| RDS PostgreSQL | db.t3.medium (2 vCPU, 4 GB), 100 GB SSD | $70 |
| ElastiCache Redis | cache.t3.small (1.5 GB) | $25 |
| S3 (backups, exports, photos) | 50 GB | $2 |
| CloudFront CDN | Minimal traffic | $5 |
| Route 53 (DNS) | 1 hosted zone | $1 |
| ECR (container registry) | 10 GB | $1 |
| CloudWatch (logs + metrics) | Basic | $10 |
| **Subtotal** | | **$234/mo** |

#### MVP Launch (Months 3-4, ~1,000 users)

| Service | Spec | Monthly Cost |
|---------|------|-------------|
| ECS Fargate (backend) | 2x 1 vCPU, 2 GB (always-on) | $60 |
| ECS Fargate (workers) | 4x 1 vCPU, 2 GB (always-on) | $120 |
| ECS Fargate (frontend) | 1x 0.5 vCPU, 1 GB | $20 |
| ECS Fargate (beat) | 1x 0.25 vCPU, 0.5 GB | $10 |
| RDS PostgreSQL | db.r6g.large (2 vCPU, 16 GB), 200 GB SSD | $250 |
| RDS Read Replica | db.r6g.large | $250 |
| ElastiCache Redis | cache.r6g.large (13 GB) | $130 |
| S3 | 200 GB + transfer | $15 |
| CloudFront CDN | 100 GB/mo transfer | $20 |
| ALB (load balancer) | 1x | $25 |
| Route 53 | 1 zone + health checks | $5 |
| ECR | 20 GB | $2 |
| CloudWatch + Sentry | Enhanced monitoring | $30 |
| NAT Gateway | 1x (for private subnet outbound) | $45 |
| **Subtotal** | | **$982/mo** |

#### Growth Phase (Months 5-12, ~10,000 users)

| Service | Spec | Monthly Cost |
|---------|------|-------------|
| ECS Fargate (backend) | 4x 2 vCPU, 4 GB (auto-scaling) | $240 |
| ECS Fargate (workers) | 8x 2 vCPU, 4 GB (auto-scaling) | $480 |
| ECS Fargate (frontend) | 2x 1 vCPU, 2 GB | $60 |
| ECS Fargate (beat) | 1x 0.5 vCPU, 1 GB | $15 |
| RDS PostgreSQL | db.r6g.xlarge (4 vCPU, 32 GB), 500 GB SSD | $520 |
| RDS Read Replicas (2x) | db.r6g.large | $500 |
| ElastiCache Redis | cache.r6g.xlarge (26 GB), cluster mode | $310 |
| S3 | 1 TB + transfer | $40 |
| CloudFront CDN | 500 GB/mo transfer | $60 |
| ALB | 1x with increased traffic | $40 |
| Route 53 | Multiple zones | $10 |
| ECR | 50 GB | $5 |
| CloudWatch + Datadog | Full observability | $150 |
| NAT Gateway | 2x (multi-AZ) | $90 |
| WAF | Basic rule set | $30 |
| **Subtotal** | | **$2,550/mo** |

### GCP Alternative (for comparison)

| Phase | GCP Equivalent | Monthly Cost |
|-------|---------------|-------------|
| Pre-Launch | Cloud Run + Cloud SQL (basic) + Memorystore | ~$200/mo |
| MVP Launch | Cloud Run (auto-scale) + Cloud SQL (HA) + Memorystore | ~$900/mo |
| Growth | GKE Autopilot + Cloud SQL (regional) + Memorystore cluster | ~$2,300/mo |

GCP is approximately 10-15% cheaper for comparable specs due to Cloud Run's per-request billing model, which is advantageous for bursty workloads.

---

## Third-Party API Costs

| Service | Plan | Monthly Cost | Usage |
|---------|------|-------------|-------|
| **BrightData** (residential proxies) | Pay-as-you-go | $500-2,000 | ~5-20 GB bandwidth, residential IPs |
| **SendGrid** (transactional email) | Essentials 50K | $20-90 | Registration, alerts, digests |
| **Mapbox** (maps + geocoding) | Pay-as-you-go | $0-500 | Free up to 50K loads, then $5/1K |
| **OpenAI** (GPT-4o) | API | $200-1,000 | ~50K-200K property analyses/mo |
| **Anthropic** (Claude, backup) | API | $0-200 | Fallback or specialized analysis |
| **Stripe** (payments) | Standard | 2.9% + $0.30/txn | ~$50-500/mo depending on volume |
| **Sentry** (error tracking) | Team | $26 | 50K events/mo |
| **Vercel** (optional frontend hosting) | Pro | $20 | Alternative to self-hosted Next.js |

### Cost by Phase

| Phase | Third-Party Total |
|-------|------------------|
| Pre-Launch | ~$800/mo |
| MVP Launch | ~$1,500/mo |
| Growth | ~$3,000/mo |

### Proxy Cost Breakdown

Proxy costs are the largest variable and depend on scraping volume:

| Listings Scraped/Day | Pages/Day (est.) | Bandwidth | BrightData Cost |
|---------------------|------------------|-----------|-----------------|
| 5,000 | 15,000 | ~3 GB | ~$500/mo |
| 20,000 | 60,000 | ~12 GB | ~$1,200/mo |
| 50,000 | 150,000 | ~30 GB | ~$2,000/mo |

### AI/LLM Cost Breakdown

| Operation | Model | Tokens/Request | Cost/Request | Volume/Mo | Monthly Cost |
|-----------|-------|---------------|-------------|-----------|-------------|
| Property summary | GPT-4o | ~2K in, ~500 out | $0.013 | 50K | $650 |
| Risk assessment | GPT-4o | ~3K in, ~800 out | $0.020 | 50K | $1,000 |
| Market insights | GPT-4o | ~4K in, ~1K out | $0.028 | 5K | $140 |
| **Optimization**: Use GPT-4o-mini for initial analysis, GPT-4o only for high-score properties ||||| |
| Property summary | GPT-4o-mini | ~2K in, ~500 out | $0.0004 | 45K | $18 |
| Deep analysis (score >70) | GPT-4o | ~3K in, ~1K out | $0.023 | 5K | $115 |
| **Optimized total** | | | | | **~$275/mo** |

---

## Team Costs

### Engineering Team (MVP Phase)

| Role | Count | Monthly Salary (US) | Monthly Total |
|------|-------|--------------------:|-------------:|
| Senior Backend Engineer | 2 | $15,000 | $30,000 |
| Senior Frontend Engineer | 1 | $14,000 | $14,000 |
| AI/ML Engineer | 1 | $16,000 | $16,000 |
| **Subtotal (salaries)** | **4** | | **$60,000** |

### With Benefits and Overhead

| Item | Monthly Cost |
|------|-------------|
| Salaries | $60,000 |
| Benefits (health, dental, 401k) ~25% | $15,000 |
| Payroll taxes ~10% | $6,000 |
| Tools (GitHub, Figma, Slack, Notion) | $500 |
| **Total people cost** | **$81,500/mo** |

### Contractor Alternative

| Role | Count | Hourly Rate | Hours/Mo | Monthly Cost |
|------|-------|-------------|----------|-------------|
| Backend (senior, US) | 2 | $150 | 160 | $48,000 |
| Frontend (senior, US) | 1 | $140 | 160 | $22,400 |
| AI/ML (senior, US) | 1 | $175 | 160 | $28,000 |
| **Total (US contractors)** | | | | **$98,400/mo** |

| Role | Count | Hourly Rate | Hours/Mo | Monthly Cost |
|------|-------|-------------|----------|-------------|
| Backend (senior, LATAM/EU) | 2 | $75 | 160 | $24,000 |
| Frontend (senior, LATAM/EU) | 1 | $70 | 160 | $11,200 |
| AI/ML (senior, LATAM/EU) | 1 | $85 | 160 | $13,600 |
| **Total (offshore contractors)** | | | | **$48,800/mo** |

---

## Monthly Burn Rate Summary

| Phase | Infrastructure | Third-Party | People (FTE) | Total Burn |
|-------|---------------|------------|-------------|------------|
| **Pre-Launch** (Mo 1-2) | $234 | $800 | $81,500 | **$82,534** |
| **MVP Launch** (Mo 3-4) | $982 | $1,500 | $81,500 | **$83,982** |
| **Growth** (Mo 5-8) | $2,550 | $3,000 | $97,500* | **$103,050** |
| **Scale** (Mo 9-12) | $4,000 | $5,000 | $130,000** | **$139,000** |

*Adding 1 engineer + 1 growth marketer in month 5
**Adding 2 more engineers + customer success in month 9

### Total Funding Required (12 Months)

| Period | Duration | Monthly Avg | Total |
|--------|----------|------------|-------|
| Pre-MVP | 2 months | $82,500 | $165,000 |
| MVP | 2 months | $84,000 | $168,000 |
| Growth | 4 months | $103,000 | $412,000 |
| Scale | 4 months | $139,000 | $556,000 |
| **Total** | **12 months** | | **$1,301,000** |

With 20% contingency buffer: **~$1,560,000**

---

## Revenue Projections

### Pricing Tiers

| Tier | Monthly | Annual (17% discount) | Target Segment |
|------|---------|----------------------|----------------|
| Free | $0 | $0 | Casual browsers, lead gen |
| Starter | $29 | $290 | New investors, 1-2 properties |
| Pro | $79 | $790 | Active investors, 3-10 properties |
| Enterprise | $199 | $1,990 | Wholesalers, funds, teams |

### Conversion Assumptions

| Metric | Assumption | Rationale |
|--------|-----------|-----------|
| Free -> Starter | 8% | Industry SaaS average for freemium |
| Starter -> Pro | 25% | Strong value prop at Pro tier |
| Pro -> Enterprise | 5% | Small percentage of power users |
| Annual vs Monthly | 40% annual | Standard SaaS ratio |
| Monthly churn (Starter) | 8% | Higher churn at entry tier |
| Monthly churn (Pro) | 4% | Stickier at higher tier |
| Monthly churn (Enterprise) | 2% | Very sticky |
| Free user acquisition | 2,000/mo by Mo 6 | SEO + content + referral |

### Revenue Ramp (Months 1-12)

| Month | Free Users | Starter | Pro | Enterprise | MRR |
|-------|-----------|---------|-----|------------|-----|
| 1 | 100 | 0 | 0 | 0 | $0 |
| 2 | 200 | 0 | 0 | 0 | $0 |
| 3 | 500 | 20 | 5 | 0 | $975 |
| 4 | 1,000 | 55 | 14 | 1 | $2,900 |
| 5 | 1,800 | 110 | 30 | 3 | $5,987 |
| 6 | 3,000 | 190 | 55 | 5 | $10,305 |
| 7 | 4,500 | 290 | 85 | 8 | $16,127 |
| 8 | 6,500 | 410 | 125 | 12 | $23,163 |
| 9 | 9,000 | 560 | 175 | 18 | $32,342 |
| 10 | 12,000 | 740 | 240 | 25 | $43,435 |
| 11 | 15,500 | 950 | 310 | 33 | $56,057 |
| 12 | 20,000 | 1,200 | 400 | 42 | $71,658 |

### Annual Revenue (Year 1)

| Metric | Value |
|--------|-------|
| Total Free Users (end of Y1) | 20,000 |
| Total Paying Users (end of Y1) | 1,642 |
| Conversion Rate (Free -> Paid) | 8.2% |
| MRR at Month 12 | $71,658 |
| ARR at Month 12 | $859,896 |
| Total Revenue (Year 1) | ~$263,000 |

### Key Revenue Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Average Revenue Per Paid User (ARPU) | $43.64/mo | Blended across tiers |
| Customer Acquisition Cost (CAC) | $25-50 | Content + SEO heavy strategy |
| Lifetime Value (LTV) - Starter | $290 | ~10 month avg lifetime |
| Lifetime Value (LTV) - Pro | $1,580 | ~20 month avg lifetime |
| Lifetime Value (LTV) - Enterprise | $7,960 | ~40 month avg lifetime |
| Blended LTV | $980 | Weighted by tier distribution |
| LTV:CAC Ratio | 20-39x | Very healthy (target >3x) |

---

## Break-Even Analysis

### Monthly Break-Even

| Phase | Monthly Burn | Required MRR | Required Paying Users |
|-------|-------------|-------------|----------------------|
| Pre-Launch | $82,500 | N/A | N/A |
| MVP (lean) | $84,000 | $84,000 | ~1,924 users at $43.64 ARPU |
| Growth | $103,000 | $103,000 | ~2,360 users |
| Scale | $139,000 | $139,000 | ~3,185 users |

### Path to Break-Even

Based on revenue projections, the company reaches MRR break-even against the Growth-phase burn rate (~$103K/mo) between **Month 13 and Month 15**, assuming:
- Continued user acquisition at 2,000-3,000 free users/month
- Conversion rates hold at 8% free-to-paid
- Churn rates remain stable

```
Revenue vs. Costs (Monthly)

$150K |                                          _____
      |                                     ___/
$120K |                                ____/
      |                           ____/
$100K |  =============================================  <-- Break-even line
      |                      ___/                         (Growth burn rate)
 $75K |                 ____/
      |            ____/
 $50K |       ____/
      |  ____/
 $25K |_/
      |_____|_____|_____|_____|_____|_____|_____|_____|
      Mo 3   Mo 5   Mo 7   Mo 9  Mo 11  Mo 13  Mo 15
```

### Runway Analysis

| Funding Raised | Monthly Burn (avg) | Runway |
|---------------|-------------------|--------|
| $500K (pre-seed) | $83,000 | ~6 months |
| $1M (pre-seed) | $95,000 (avg) | ~10.5 months |
| $1.5M (seed) | $100,000 (avg) | ~15 months |
| $2M (seed) | $105,000 (avg) | ~19 months |

**Recommendation**: Raise $1.5-2M seed round to provide 15-19 months of runway, allowing the company to reach break-even with buffer for unexpected costs and market conditions.

---

## Cost Optimization Strategies

| Strategy | Potential Savings | Implementation |
|----------|------------------|----------------|
| Spot/Preemptible instances for workers | 60-70% on compute | Month 3+ |
| Reserved instances for database | 30-40% on RDS | Month 6+ (1-year commitment) |
| GPT-4o-mini for initial analysis | 80% on AI costs | Month 1 |
| Aggressive Redis caching | 30% on DB load | Month 2+ |
| S3 lifecycle policies | 50% on storage | Month 3+ |
| CDN caching of API responses | 20% on compute | Month 4+ |
| Negotiate BrightData annual contract | 20-30% on proxies | Month 6+ |
