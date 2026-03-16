"""AI Lease Analyzer — Extract structured data and risk assessment from leases."""

import json
from dataclasses import dataclass

import anthropic


@dataclass
class LeaseField:
    name: str
    value: str | None
    source_text: str | None  # Original clause text


@dataclass
class Risk:
    name: str
    severity: str  # high | medium | low
    clause_text: str
    explanation: str


@dataclass
class LeaseAnalysis:
    fields: dict[str, LeaseField]
    risks: list[Risk]
    risk_score: int  # 0-100
    summary: str
    missing_clauses: list[str]
    key_dates: list[dict]


ANALYSIS_PROMPT = """Analyze this residential lease agreement. Extract key terms and identify risks.

LEASE TEXT:
{lease_text}

Respond in JSON format:
{{
    "fields": {{
        "lease_type": "fixed|month_to_month",
        "start_date": "YYYY-MM-DD or null",
        "end_date": "YYYY-MM-DD or null",
        "monthly_rent": number or null,
        "security_deposit": number or null,
        "late_fee_amount": number or null,
        "late_fee_grace_days": number or null,
        "rent_due_day": number or null,
        "termination_notice_days": number or null,
        "entry_notice_hours": number or null,
        "pet_policy": "allowed|not_allowed|with_deposit|not_mentioned",
        "pet_deposit": number or null,
        "subletting_allowed": true|false|null,
        "insurance_required": true|false|null,
        "utilities_included": ["list"] or [],
        "parking_included": true|false|null,
        "renewal_terms": "description or null",
        "maintenance_tenant_responsibility": "description or null"
    }},
    "risks": [
        {{
            "name": "short identifier",
            "severity": "high|medium|low",
            "clause_text": "the exact clause from the lease",
            "explanation": "why this is a risk and what to watch for"
        }}
    ],
    "missing_clauses": ["list of standard clauses not found in the lease"],
    "summary": "2-3 sentence plain-English summary of the lease terms",
    "key_dates": [
        {{"event": "lease_start", "date": "YYYY-MM-DD"}},
        {{"event": "lease_end", "date": "YYYY-MM-DD"}}
    ]
}}

Standard clauses to check for:
- Rent amount and due date
- Security deposit and return timeline
- Late fee terms
- Maintenance responsibilities
- Entry/access notice period
- Termination and renewal terms
- Pet policy
- Subletting policy
- Insurance requirements
- Lead paint disclosure (if applicable)
- Dispute resolution
- Habitability warranty

IMPORTANT: You are flagging items for review, not providing legal advice.
Only respond with JSON."""


class LeaseAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    async def analyze(self, lease_text: str) -> LeaseAnalysis:
        """Analyze lease text and return structured analysis."""

        response = self.client.messages.create(
            model="claude-opus-4-6-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": ANALYSIS_PROMPT.format(lease_text=lease_text[:50000]),
            }],
        )

        result = json.loads(response.content[0].text)

        # Build structured fields
        fields = {}
        for name, value in result["fields"].items():
            fields[name] = LeaseField(
                name=name,
                value=value,
                source_text=None,  # Could be enhanced with citation
            )

        # Build risk objects
        risks = [
            Risk(
                name=r["name"],
                severity=r["severity"],
                clause_text=r["clause_text"],
                explanation=r["explanation"],
            )
            for r in result.get("risks", [])
        ]

        # Calculate risk score
        risk_score = self._calculate_risk_score(risks, result.get("missing_clauses", []))

        return LeaseAnalysis(
            fields=fields,
            risks=risks,
            risk_score=risk_score,
            summary=result.get("summary", ""),
            missing_clauses=result.get("missing_clauses", []),
            key_dates=result.get("key_dates", []),
        )

    def _calculate_risk_score(
        self, risks: list[Risk], missing_clauses: list[str]
    ) -> int:
        """Calculate 0-100 risk score. Higher = more risky."""
        score = 0

        severity_weights = {"high": 20, "medium": 10, "low": 5}
        for risk in risks:
            score += severity_weights.get(risk.severity, 5)

        # Missing clauses add risk
        score += len(missing_clauses) * 5

        return min(score, 100)
