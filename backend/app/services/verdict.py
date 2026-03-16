"""AI verdict synthesis using Claude API."""

import json
import logging
from typing import Any, Optional

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_verdict(
    property_data: dict[str, Any],
    rent_estimate: dict[str, Any],
    metrics: dict[str, Any],
    neighborhood: Optional[dict[str, Any]],
    investment_score: int,
) -> Optional[dict[str, Any]]:
    """
    Generate an AI-powered investment verdict using Claude.

    Returns dict with: verdict, confidence, summary, risks, opportunities.
    Returns None if API key is missing or call fails.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set, using rule-based verdict")
        return _rule_based_verdict(metrics, neighborhood, investment_score)

    prompt = _build_prompt(property_data, rent_estimate, metrics, neighborhood, investment_score)

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text

        # Parse structured response
        parsed = _parse_verdict_response(raw)
        logger.info("AI verdict generated: %s", parsed.get("verdict"))
        return parsed

    except Exception as e:
        logger.error("Claude API failed, falling back to rule-based: %s", e)
        return _rule_based_verdict(metrics, neighborhood, investment_score)


def _build_prompt(
    prop: dict, rent: dict, metrics: dict, hood: Optional[dict], score: int
) -> str:
    hood_section = ""
    if hood:
        hood_section = f"""
Neighborhood:
- Crime Index: {hood.get('crime_rate', 'N/A')}/100 ({hood.get('crime_label', 'Unknown')})
- School Rating: {hood.get('school_rating', 'N/A')}/10
- Population Growth: {hood.get('pop_growth', 'N/A')}%/yr
- Rent Growth: {hood.get('rent_growth', 'N/A')}%/yr
- Median Income: ${hood.get('median_income', 'N/A'):,}
- Unemployment: {hood.get('unemployment', 'N/A')}%"""

    return f"""You are an expert real estate investment analyst. Analyze this property and provide a structured verdict.

Property:
- Address: {prop.get('address', 'Unknown')}
- Price: ${prop.get('price', 0):,.0f}
- Beds/Baths: {prop.get('beds', 'N/A')}/{prop.get('baths', 'N/A')}
- Sqft: {prop.get('sqft', 'N/A'):,}
- Year Built: {prop.get('year_built', 'N/A')}
- HOA: ${prop.get('hoa', 0):,.0f}/mo

Rent Estimate: ${rent.get('amount', 0):,.0f}/mo (confidence: {rent.get('confidence', 0):.0f}%)

Investment Metrics:
- Investment Score: {score}/100
- Cap Rate: {metrics.get('cap_rate', 0):.1f}%
- Monthly Cash Flow: ${metrics.get('monthly_cash_flow', 0):,.0f}
- Cash-on-Cash: {metrics.get('cash_on_cash', 0):.1f}%
- DSCR: {metrics.get('dscr', 0):.2f}
- BRRRR Score: {metrics.get('brrrr_score', 0):.0f}/100 ({metrics.get('brrrr_rating', 'N/A')})
- Flip ROI: {metrics.get('flip_roi', 0):.1f}% ({metrics.get('flip_rating', 'N/A')})
{hood_section}

Respond ONLY with valid JSON in this exact format:
{{
  "verdict": "Good Deal" | "Average" | "Avoid",
  "confidence": "High" | "Medium" | "Low",
  "summary": "2-3 sentence investment analysis",
  "risks": ["risk 1", "risk 2", "risk 3"],
  "opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"]
}}"""


def _parse_verdict_response(raw: str) -> dict[str, Any]:
    """Parse Claude's JSON response, with fallback extraction."""
    # Try direct JSON parse
    try:
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: extract from text
    verdict = "Average"
    if "good deal" in raw.lower():
        verdict = "Good Deal"
    elif "avoid" in raw.lower():
        verdict = "Avoid"

    return {
        "verdict": verdict,
        "confidence": "Medium",
        "summary": raw[:300],
        "risks": [],
        "opportunities": [],
    }


def _rule_based_verdict(
    metrics: dict, hood: Optional[dict], score: int
) -> dict[str, Any]:
    """Deterministic verdict when Claude is unavailable."""
    cap = metrics.get("cap_rate", 0)
    cf = metrics.get("monthly_cash_flow", 0)
    coc = metrics.get("cash_on_cash", 0)

    risks = []
    opps = []

    # Determine verdict
    if score >= 70 and cap >= 7 and cf > 200:
        verdict = "Good Deal"
        confidence = "High"
    elif score >= 50 and (cap >= 5 or cf > 0):
        verdict = "Average"
        confidence = "Medium"
    else:
        verdict = "Avoid"
        confidence = "Medium" if score >= 30 else "High"

    # Build risks
    if cap < 5:
        risks.append(f"Low cap rate ({cap:.1f}%) — below the 5% minimum for positive leverage")
    if cf < 0:
        risks.append(f"Negative cash flow (${cf:,.0f}/mo) — you'd be subsidizing this property")
    if hood and hood.get("crime_rate", 0) > 60:
        risks.append("High crime area may affect tenant quality and appreciation")
    if hood and hood.get("pop_growth") is not None and hood["pop_growth"] < 0:
        risks.append("Declining population suggests weakening rental demand")
    if not risks:
        risks.append("No major red flags identified")

    # Build opportunities
    if cap >= 8:
        opps.append(f"Strong {cap:.1f}% cap rate — above-market returns")
    if coc > 10:
        opps.append(f"Excellent cash-on-cash return of {coc:.1f}%")
    if hood and hood.get("rent_growth", 0) > 4:
        opps.append(f"Strong rent growth ({hood['rent_growth']:.1f}%/yr) suggests rising income")
    if hood and hood.get("school_rating", 0) >= 8:
        opps.append(f"Top-rated schools ({hood['school_rating']}/10) attract quality tenants")
    if not opps:
        opps.append("Market conditions are stable")

    summary_parts = []
    if verdict == "Good Deal":
        summary_parts.append(f"This property scores {score}/100 with strong fundamentals.")
    elif verdict == "Average":
        summary_parts.append(f"This property scores {score}/100 with mixed signals.")
    else:
        summary_parts.append(f"This property scores {score}/100 and doesn't meet investment thresholds.")

    if cf > 0:
        summary_parts.append(f"Positive cash flow of ${cf:,.0f}/mo with {cap:.1f}% cap rate.")
    else:
        summary_parts.append(f"Negative cash flow of ${cf:,.0f}/mo makes this a risky hold.")

    return {
        "verdict": verdict,
        "confidence": confidence,
        "summary": " ".join(summary_parts),
        "risks": risks[:3],
        "opportunities": opps[:3],
    }
