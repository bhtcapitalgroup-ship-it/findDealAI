# RealDeal AI — AI Modules Design

---

## 1. AI Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI SERVICE                                │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ TenantBot   │  │ Vision       │  │ Document Intelligence  │ │
│  │ (Chat Agent)│  │ Diagnostics  │  │                        │ │
│  │             │  │              │  │  ┌──────────────────┐  │ │
│  │ • Intent    │  │ • Photo      │  │  │ Lease Analyzer   │  │ │
│  │   Classify  │  │   Analysis   │  │  ├──────────────────┤  │ │
│  │ • Entity    │  │ • Severity   │  │  │ OCR Pipeline     │  │ │
│  │   Extract   │  │   Scoring    │  │  ├──────────────────┤  │ │
│  │ • Response  │  │ • Cost       │  │  │ Auto-Tagging     │  │ │
│  │   Generate  │  │   Estimate   │  │  └──────────────────┘  │ │
│  │ • Escalate  │  │              │  │                        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Shared Components                        │   │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐            │   │
│  │  │ Prompt   │  │ Guard     │  │ Context    │            │   │
│  │  │ Manager  │  │ Rails     │  │ Assembler  │            │   │
│  │  └──────────┘  └───────────┘  └────────────┘            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Module 1: TenantBot (Communication AI)

### 2.1 Intent Classification

```python
INTENT_TAXONOMY = {
    "maintenance": {
        "subtypes": ["plumbing", "electrical", "hvac", "appliance",
                     "structural", "pest", "lockout", "other"],
        "handler": "maintenance_flow"
    },
    "payment": {
        "subtypes": ["balance_inquiry", "payment_receipt", "payment_plan",
                     "dispute", "late_fee_question"],
        "handler": "payment_flow"
    },
    "lease": {
        "subtypes": ["renewal", "termination", "subletting", "terms_question",
                     "move_out", "move_in"],
        "handler": "lease_flow"
    },
    "complaint": {
        "subtypes": ["noise", "neighbor", "common_area", "safety"],
        "handler": "escalation_flow"  # Always escalate complaints
    },
    "general": {
        "subtypes": ["amenity_question", "parking", "package", "access",
                     "greeting", "other"],
        "handler": "general_flow"
    }
}
```

### 2.2 Chat Agent Pipeline

```python
class TenantChatAgent:
    """
    Stateful agent that manages tenant conversations.
    Each conversation maintains context across messages.
    """

    async def process_message(self, tenant_id: str, message: str,
                               attachments: list[str] = None) -> AgentResponse:
        # 1. Load context
        context = await self.build_context(tenant_id)
        # Includes: tenant info, unit, lease terms, open requests,
        #           payment status, recent conversation history

        # 2. Classify intent
        classification = await self.classify_intent(message, context)
        # Returns: {intent, subtype, confidence, entities}

        # 3. Guard rails check
        if self.triggers_escalation(classification, message):
            return await self.escalate(tenant_id, message, reason="policy")

        # 4. Route to handler
        handler = self.get_handler(classification.intent)
        action_result = await handler.process(classification, context)

        # 5. Generate response
        response = await self.generate_response(
            message=message,
            classification=classification,
            action_result=action_result,
            context=context,
            tone="professional_empathetic"
        )

        # 6. Log and return
        await self.log_interaction(tenant_id, message, response, classification)
        return response
```

### 2.3 Context Assembly

```python
async def build_context(self, tenant_id: str) -> TenantContext:
    """Assemble all relevant context for the AI to respond accurately."""
    return TenantContext(
        tenant=await self.get_tenant(tenant_id),
        unit=await self.get_unit(tenant_id),
        lease=await self.get_active_lease(tenant_id),
        payment_status=await self.get_payment_status(tenant_id),
        open_requests=await self.get_open_maintenance(tenant_id),
        recent_messages=await self.get_recent_messages(tenant_id, limit=20),
        property_rules=await self.get_property_rules(tenant_id),
        landlord_preferences=await self.get_ai_settings(tenant_id),
    )
```

### 2.4 System Prompt Template

```
You are a professional AI property management assistant for {property_name}.
You help tenants with maintenance requests, payment questions, and lease inquiries.

RULES:
- Never provide legal advice. Say "I'd recommend consulting with a legal professional."
- Never make promises about rent reductions or lease modifications.
- Never discuss other tenants or share their information.
- Always be empathetic about maintenance issues and responsive to urgency.
- If unsure, escalate to the property manager rather than guessing.
- Do not discuss property value, sale plans, or ownership details.

TENANT CONTEXT:
- Name: {tenant.first_name}
- Unit: {unit.unit_number}
- Lease: {lease.start_date} to {lease.end_date}
- Rent: ${lease.rent_amount}/month, due on day {lease.rent_due_day}
- Payment status: {payment_status}
- Open maintenance requests: {open_requests}

PROPERTY RULES:
{property_rules}
```

### 2.5 Escalation Triggers

```python
ESCALATION_TRIGGERS = {
    "keyword_patterns": [
        r"\b(lawyer|attorney|sue|legal action|lawsuit)\b",
        r"\b(discriminat|harass|threaten|unsafe|danger)\b",
        r"\b(health department|code violation|inspector)\b",
        r"\b(withhold rent|rent strike)\b",
    ],
    "conditions": [
        lambda c: c.confidence < 0.7,
        lambda c: c.intent == "complaint",
        lambda c: c.sentiment_score < -0.6,
        lambda c: c.message_count_today > 10,  # Excessive contact
    ]
}
```

---

## 3. Module 2: Vision Diagnostics

### 3.1 Photo Analysis Pipeline

```python
class MaintenanceDiagnostics:
    """Analyze tenant-submitted photos to diagnose maintenance issues."""

    ISSUE_CATEGORIES = {
        "water_damage": {
            "indicators": ["stains", "discoloration", "bubbling paint",
                          "warped material", "pooling water"],
            "urgency_default": "urgent",
            "trade": "plumbing"
        },
        "mold": {
            "indicators": ["dark spots", "fuzzy growth", "discoloration"],
            "urgency_default": "urgent",  # Health hazard
            "trade": "remediation"
        },
        "structural_damage": {
            "indicators": ["cracks", "holes", "sagging", "separation"],
            "urgency_default": "urgent",
            "trade": "general_contractor"
        },
        "hvac_issue": {
            "indicators": ["frost buildup", "discolored vents", "visible damage"],
            "urgency_default": "routine",
            "trade": "hvac"
        },
        "electrical": {
            "indicators": ["scorch marks", "exposed wiring", "damaged outlets"],
            "urgency_default": "emergency",  # Fire hazard
            "trade": "electrician"
        },
        "appliance_damage": {
            "indicators": ["broken parts", "leaking", "rust", "malfunction signs"],
            "urgency_default": "routine",
            "trade": "appliance_repair"
        },
        "pest_evidence": {
            "indicators": ["droppings", "damage patterns", "nesting material"],
            "urgency_default": "urgent",
            "trade": "pest_control"
        }
    }

    async def diagnose(self, image_keys: list[str],
                       description: str = "") -> Diagnosis:
        # 1. Send to vision model
        vision_result = await self.analyze_images(image_keys)

        # 2. Cross-reference with text description
        combined = await self.merge_signals(vision_result, description)

        # 3. Generate diagnosis
        return Diagnosis(
            category=combined.primary_category,
            confidence=combined.confidence,
            severity=combined.severity,          # 1-5
            urgency=combined.urgency,            # emergency|urgent|routine
            description=combined.ai_description,
            recommended_trade=combined.trade,
            estimated_cost_range=self.estimate_cost(combined),
            recommended_action=combined.action,
            raw_analysis=combined.raw
        )

    async def analyze_images(self, image_keys: list[str]) -> VisionResult:
        """Send images to Claude vision with diagnostic prompt."""
        images = [await self.load_from_s3(key) for key in image_keys]

        response = await self.claude_client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    *[{"type": "image", "source": img} for img in images],
                    {"type": "text", "text": DIAGNOSIS_PROMPT}
                ]
            }]
        )
        return self.parse_vision_response(response)
```

### 3.2 Vision Prompt

```
Analyze this photo from a residential rental property maintenance request.

Identify:
1. PRIMARY ISSUE: What is the main problem visible? (water_damage | mold |
   structural_damage | hvac_issue | electrical | appliance_damage | pest_evidence | other)
2. SEVERITY: Rate 1-5 (1=cosmetic, 3=functional impact, 5=safety hazard)
3. DESCRIPTION: What specifically do you see? Be precise about location and extent.
4. POSSIBLE CAUSES: What likely caused this?
5. RECOMMENDED ACTION: What should the landlord do?
6. URGENCY: emergency (safety risk, ≤4h) | urgent (habitability impact, ≤24h) |
   routine (non-critical, ≤7d)
7. TRADE NEEDED: What type of contractor should handle this?

Respond in JSON format.
```

### 3.3 Cost Estimation

```python
# Regional cost database (updated quarterly)
COST_ESTIMATES = {
    "plumbing": {
        "minor": (150, 400),    # Faucet repair, unclog
        "moderate": (400, 1200), # Pipe repair, toilet replace
        "major": (1200, 5000),   # Pipe replacement, water heater
    },
    "electrical": {
        "minor": (100, 300),
        "moderate": (300, 800),
        "major": (800, 3000),
    },
    "hvac": {
        "minor": (100, 350),
        "moderate": (350, 1500),
        "major": (1500, 6000),
    },
    # ... more trades
}

def estimate_cost(self, diagnosis: CombinedDiagnosis) -> tuple[float, float]:
    trade = diagnosis.trade
    if diagnosis.severity <= 2:
        tier = "minor"
    elif diagnosis.severity <= 4:
        tier = "moderate"
    else:
        tier = "major"
    return COST_ESTIMATES.get(trade, {}).get(tier, (200, 2000))
```

---

## 4. Module 3: Lease Analyzer

### 4.1 Analysis Pipeline

```python
class LeaseAnalyzer:
    """Extract structured data and risk assessment from lease documents."""

    async def analyze(self, document_id: str) -> LeaseAnalysis:
        # 1. Get document text (OCR if needed)
        doc = await self.get_document(document_id)
        text = doc.ocr_text or await self.ocr_pipeline(doc.s3_key)

        # 2. Extract structured fields
        fields = await self.extract_fields(text)

        # 3. Identify risk factors
        risks = await self.assess_risks(text, fields)

        # 4. Generate summary
        summary = await self.generate_summary(text, fields, risks)

        return LeaseAnalysis(
            fields=fields,
            risks=risks,
            risk_score=self.calculate_risk_score(risks),
            summary=summary,
            key_dates=self.extract_dates(fields),
            missing_clauses=self.find_missing_clauses(fields)
        )

    STANDARD_CLAUSES = [
        "rent_amount", "security_deposit", "lease_term",
        "late_fee", "maintenance_responsibility",
        "entry_notice_period", "termination_clause",
        "renewal_terms", "pet_policy", "subletting",
        "insurance_requirement", "dispute_resolution",
        "lead_paint_disclosure",  # Required for pre-1978
    ]

    RISK_PATTERNS = [
        {
            "name": "unlimited_landlord_entry",
            "pattern": "landlord may enter at any time|without notice",
            "severity": "high",
            "explanation": "Most states require 24-48 hour notice before entry"
        },
        {
            "name": "excessive_late_fee",
            "check": lambda fields: fields.late_fee_pct > 10,
            "severity": "medium",
            "explanation": "Late fee exceeds 10% of rent, may not be enforceable"
        },
        {
            "name": "no_habitability_clause",
            "check": lambda fields: not fields.has_habitability,
            "severity": "high",
            "explanation": "Missing implied warranty of habitability language"
        },
        {
            "name": "blanket_liability_waiver",
            "pattern": "tenant waives all claims|landlord not liable for any",
            "severity": "high",
            "explanation": "Overly broad liability waivers are often unenforceable"
        },
        {
            "name": "automatic_renewal_no_notice",
            "pattern": "automatically renew|auto-renew",
            "check": lambda fields: not fields.renewal_notice_days,
            "severity": "medium",
            "explanation": "Auto-renewal without notice period specified"
        },
    ]
```

### 4.2 Lease Analysis Prompt

```
You are a lease analysis assistant. Extract the following fields from this
residential lease agreement and assess risks.

EXTRACT THESE FIELDS (use null if not found):
- lease_type: "fixed" or "month_to_month"
- start_date, end_date
- monthly_rent
- security_deposit
- late_fee_amount, late_fee_grace_days
- rent_due_day
- lease_term_months
- renewal_terms
- termination_notice_days
- entry_notice_hours (landlord entry)
- pet_policy: "allowed" | "not_allowed" | "with_deposit"
- pet_deposit
- subletting_allowed: boolean
- maintenance_tenant_responsibility (what tenant must handle)
- utilities_included: list
- parking_included: boolean
- insurance_required: boolean

FLAG THESE RISKS:
- Clauses that may be unenforceable in the property's state
- Missing standard protections (habitability, security deposit return timeline)
- Unusual or one-sided terms
- Ambiguous language that could cause disputes

For each risk, provide: clause text, risk level (high/medium/low), explanation.

IMPORTANT: You are not providing legal advice. Flag issues for review by a
qualified attorney.
```

---

## 5. Module 4: Financial Intelligence

```python
class FinancialAI:
    """AI-powered financial insights for the dashboard."""

    async def generate_insights(self, landlord_id: str) -> list[Insight]:
        data = await self.get_financial_data(landlord_id)

        insights = []

        # Rent collection trend
        if data.collection_rate < 0.95:
            insights.append(Insight(
                type="warning",
                title="Collection rate below target",
                body=f"Only {data.collection_rate:.0%} collected this month. "
                     f"{data.delinquent_count} tenants past due.",
                action="View aging report"
            ))

        # Expense anomaly detection
        for prop in data.properties:
            if prop.maintenance_spend > prop.avg_maintenance * 1.5:
                insights.append(Insight(
                    type="alert",
                    title=f"High maintenance spend: {prop.name}",
                    body=f"${prop.maintenance_spend:,.0f} this month vs "
                         f"${prop.avg_maintenance:,.0f} average. "
                         f"Review recent repairs.",
                    action="View maintenance history"
                ))

        # Lease expiration alerts
        expiring = [l for l in data.leases if l.days_until_expiry <= 90]
        if expiring:
            insights.append(Insight(
                type="info",
                title=f"{len(expiring)} leases expiring within 90 days",
                body="Consider sending renewal offers.",
                action="View expiring leases"
            ))

        # Vacancy cost
        if data.vacancy_rate > 0:
            monthly_loss = data.total_vacant_market_rent
            insights.append(Insight(
                type="info",
                title=f"Vacancy costing ${monthly_loss:,.0f}/month",
                body=f"{data.vacant_units} vacant units across portfolio.",
                action="View vacant units"
            ))

        return insights
```

---

## 6. Shared Components

### 6.1 Guard Rails

```python
class AIGuardRails:
    """Ensure AI outputs comply with Fair Housing and legal requirements."""

    BLOCKED_TOPICS = [
        "race", "religion", "national_origin", "sex", "familial_status",
        "disability", "sexual_orientation", "gender_identity",
        "source_of_income",  # Protected in many states
    ]

    async def check_response(self, response: str) -> GuardResult:
        # 1. Fair Housing compliance
        fh_check = await self.fair_housing_check(response)
        if not fh_check.passed:
            return GuardResult(blocked=True, reason="fair_housing", detail=fh_check)

        # 2. No legal advice
        if self.contains_legal_advice(response):
            return GuardResult(blocked=True, reason="legal_advice")

        # 3. No PII leakage (other tenants)
        if self.contains_other_tenant_pii(response):
            return GuardResult(blocked=True, reason="pii_leakage")

        # 4. No financial promises
        if self.contains_financial_promise(response):
            return GuardResult(blocked=True, reason="financial_promise")

        return GuardResult(blocked=False)
```

### 6.2 Prompt Manager

```python
class PromptManager:
    """Version-controlled prompt templates with A/B testing support."""

    def __init__(self):
        self.templates: dict[str, PromptTemplate] = {}
        self.active_experiments: dict[str, Experiment] = {}

    async def get_prompt(self, name: str, variables: dict) -> str:
        template = self.templates[name]

        # Check for active A/B test
        if name in self.active_experiments:
            template = self.active_experiments[name].select_variant()

        return template.render(**variables)

    async def log_outcome(self, prompt_id: str, outcome: dict):
        """Track prompt effectiveness for optimization."""
        await self.metrics.log(prompt_id, outcome)
```

---

## 7. Model Selection Strategy

| Task | Model | Rationale |
|------|-------|-----------|
| Intent classification | Claude Haiku 4.5 | Fast, cheap, high accuracy for classification |
| Chat response generation | Claude Sonnet 4.6 | Good balance of quality and speed |
| Vision diagnostics | Claude Sonnet 4.6 | Strong vision + reasoning |
| Lease analysis | Claude Opus 4.6 | Complex document understanding, highest accuracy |
| OCR pre-processing | Tesseract / AWS Textract | Cost-effective for text extraction |
| Embeddings (future) | Voyage-3 | For semantic search over documents |

### Cost Optimization

```
Per-tenant monthly AI cost estimate (active tenant):
  ~15 messages/month × $0.003/message (Haiku classify + Sonnet respond) = $0.045
  ~1 photo diagnosis/month × $0.02/image                                = $0.020
  ~0.1 lease analyses/month × $0.15/analysis                            = $0.015
                                                              Total:     ~$0.08/tenant/month

For 50-unit landlord: ~$4/month in AI costs
```
