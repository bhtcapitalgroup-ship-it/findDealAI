"""
RealDeal AI - Analysis Celery Tasks

Runs deal analysis pipelines, batch scoring, alert checking, and
investment score recalculation.
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional

from app.tasks.celery_app import app

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@app.task(
    bind=True,
    name="app.tasks.analysis_tasks.analyze_property",
    max_retries=2,
    default_retry_delay=30,
    rate_limit="10/m",
    soft_time_limit=120,
)
def analyze_property(self, property_id: str) -> dict[str, Any]:
    """
    Run the full deal analysis pipeline on a single property.

    Steps:
    1. Load property and market data
    2. Fetch comparable sales
    3. Calculate ARV
    4. Estimate rehab costs
    5. Estimate rent (if missing)
    6. Calculate financial metrics (cap rate, cash flow, CoC, DSCR)
    7. Calculate BRRRR score
    8. Calculate investment score
    9. Generate AI summary
    10. Store results and trigger alerts
    """
    logger.info("Analyzing property %s", property_id)

    try:
        from app.ai.deal_analyzer import DealAnalyzer, MarketData, PropertyData

        # Load data
        property_data = _load_property(property_id)
        if not property_data:
            return {"error": "Property not found", "property_id": property_id}

        market_data = _load_market_data(property_data.city, property_data.state)
        comps = _load_comparable_sales(property_data)

        analyzer = DealAnalyzer(anthropic_api_key=ANTHROPIC_API_KEY)

        # ARV
        arv = analyzer.calculate_arv(property_data, comps)

        # Rehab costs
        rehab_low, rehab_high = analyzer.estimate_rehab_cost(property_data)

        # Rent estimate (if not already set)
        if property_data.estimated_rent <= 0:
            property_data.estimated_rent = analyzer.estimate_rent(
                property_data, market_data
            )

        # Financial metrics
        cap_rate = analyzer.calculate_cap_rate(property_data)
        cash_flow = analyzer.calculate_cash_flow(property_data)
        cash_on_cash = analyzer.calculate_cash_on_cash(property_data)
        dscr = analyzer.calculate_dscr(property_data)
        brrrr_score = analyzer.calculate_brrrr_score(property_data)
        investment_score = analyzer.calculate_investment_score(
            property_data, market_data
        )

        analysis = {
            "property_id": property_id,
            "arv": arv,
            "rehab_low": rehab_low,
            "rehab_high": rehab_high,
            "estimated_rent": property_data.estimated_rent,
            "cap_rate": cap_rate,
            "cash_flow": cash_flow,
            "cash_on_cash": cash_on_cash,
            "dscr": dscr,
            "brrrr_score": brrrr_score,
            "investment_score": investment_score,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        # AI summary (only for high-scoring properties to manage API costs)
        if investment_score >= 50:
            try:
                summary = analyzer.generate_ai_summary(property_data, analysis)
                analysis["ai_summary"] = summary
            except Exception as exc:
                logger.warning("AI summary failed for %s: %s", property_id, exc)
                analysis["ai_summary"] = ""
        else:
            analysis["ai_summary"] = ""

        # Store analysis results
        _store_analysis(property_id, analysis)

        # Update the property's investment score in the main table
        _update_property_score(property_id, investment_score, property_data.estimated_rent)

        logger.info(
            "Analysis complete for %s: score=%d, cap=%.1f%%, cf=$%,.0f",
            property_id,
            investment_score,
            cap_rate * 100,
            cash_flow,
        )
        return analysis

    except Exception as exc:
        logger.error("Analysis failed for %s: %s", property_id, exc)
        raise self.retry(exc=exc)


@app.task(
    name="app.tasks.analysis_tasks.batch_analyze_properties",
    soft_time_limit=600,
    time_limit=900,
)
def batch_analyze_properties(property_ids: list[str]) -> dict[str, Any]:
    """
    Run analysis on a batch of properties.
    Dispatches individual analyze_property tasks for parallelism.
    """
    logger.info("Batch analysis started for %d properties", len(property_ids))

    from celery import group

    tasks = [analyze_property.s(pid) for pid in property_ids]

    # Execute as a group for parallel processing
    job = group(tasks)
    result = job.apply_async()

    return {
        "batch_size": len(property_ids),
        "task_group_id": result.id,
        "queued_at": datetime.utcnow().isoformat(),
    }


@app.task(
    name="app.tasks.analysis_tasks.check_alerts",
    soft_time_limit=300,
    time_limit=600,
)
def check_alerts() -> dict[str, Any]:
    """
    Check all active user alerts against recently analyzed properties.
    Send notifications for matches.
    """
    logger.info("Checking alerts")

    alerts = _load_active_alerts()
    recent_properties = _load_recently_analyzed_properties(minutes=30)

    if not alerts or not recent_properties:
        return {
            "alerts_checked": len(alerts),
            "properties_checked": len(recent_properties),
            "notifications_sent": 0,
        }

    notifications_sent = 0

    for alert in alerts:
        matching_properties = _match_alert(alert, recent_properties)

        if not matching_properties:
            continue

        # Send notification for each match
        for prop, analysis in matching_properties:
            try:
                _send_alert_notification(alert, prop, analysis)
                notifications_sent += 1
            except Exception as exc:
                logger.error(
                    "Failed to send alert notification for user %s, property %s: %s",
                    alert.get("user_id"),
                    analysis.get("property_id"),
                    exc,
                )

    result = {
        "alerts_checked": len(alerts),
        "properties_checked": len(recent_properties),
        "notifications_sent": notifications_sent,
        "checked_at": datetime.utcnow().isoformat(),
    }
    logger.info("Alert check complete: %s", result)
    return result


@app.task(
    name="app.tasks.analysis_tasks.update_investment_scores",
    soft_time_limit=600,
    time_limit=1200,
)
def update_investment_scores() -> dict[str, Any]:
    """
    Recalculate investment scores when market data changes.
    Only re-scores properties in markets that have updated data.
    """
    logger.info("Updating investment scores")

    from app.ai.deal_analyzer import DealAnalyzer

    analyzer = DealAnalyzer(anthropic_api_key=ANTHROPIC_API_KEY)

    # Find markets with recently updated data
    updated_markets = _load_recently_updated_markets(hours=24)
    total_updated = 0

    for market_info in updated_markets:
        city = market_info.get("city", "")
        state = market_info.get("state", "")
        market_data = _load_market_data(city, state)

        properties = _load_market_properties_with_analysis(city, state)

        for prop_id, prop, old_score in properties:
            try:
                new_score = analyzer.calculate_investment_score(prop, market_data)

                if new_score != old_score:
                    _update_property_score(prop_id, new_score, prop.estimated_rent)
                    total_updated += 1

                    # If score improved significantly, rerun full analysis
                    if new_score - old_score >= 10:
                        analyze_property.delay(prop_id)

            except Exception as exc:
                logger.debug("Score update failed for %s: %s", prop_id, exc)

    result = {
        "markets_checked": len(updated_markets),
        "scores_updated": total_updated,
        "completed_at": datetime.utcnow().isoformat(),
    }
    logger.info("Investment score update complete: %s", result)
    return result


# ---------------------------------------------------------------------------
# Alert matching logic
# ---------------------------------------------------------------------------


def _match_alert(alert: dict, properties: list) -> list:
    """
    Match a user alert against a list of recently analyzed properties.

    Alert criteria can include:
    - min_score: minimum investment score
    - max_price: maximum purchase price
    - min_cash_flow: minimum monthly cash flow
    - min_cap_rate: minimum cap rate
    - min_brrrr_score: minimum BRRRR score
    - markets: list of (city, state) tuples
    - property_types: list of property types
    - min_beds: minimum bedrooms
    - max_beds: maximum bedrooms
    """
    matches = []

    for prop, analysis in properties:
        score = analysis.get("investment_score", 0)
        price = prop.price
        cash_flow = analysis.get("cash_flow", 0)
        cap_rate = analysis.get("cap_rate", 0)
        brrrr = analysis.get("brrrr_score", 0)

        # Check each criterion
        if alert.get("min_score") and score < alert["min_score"]:
            continue
        if alert.get("max_price") and price > alert["max_price"]:
            continue
        if alert.get("min_cash_flow") and cash_flow < alert["min_cash_flow"]:
            continue
        if alert.get("min_cap_rate") and cap_rate < alert["min_cap_rate"]:
            continue
        if alert.get("min_brrrr_score") and brrrr < alert["min_brrrr_score"]:
            continue

        # Market filter
        if alert.get("markets"):
            prop_market = (prop.city.lower(), prop.state.lower())
            alert_markets = [
                (m[0].lower(), m[1].lower()) for m in alert["markets"]
            ]
            if prop_market not in alert_markets:
                continue

        # Property type filter
        if alert.get("property_types"):
            if prop.property_type not in alert["property_types"]:
                continue

        # Bedroom filter
        if alert.get("min_beds") and prop.bedrooms < alert["min_beds"]:
            continue
        if alert.get("max_beds") and prop.bedrooms > alert["max_beds"]:
            continue

        matches.append((prop, analysis))

    return matches


def _send_alert_notification(alert: dict, prop, analysis: dict) -> None:
    """Send a deal alert notification to the user."""
    from app.services.notification import NotificationService

    notification_svc = NotificationService()

    user_id = alert.get("user_id", "")
    user_email = alert.get("user_email", "")
    alert_name = alert.get("name", "Deal Alert")

    subject = (
        f"RealDeal AI Alert: {prop.address}, {prop.city} - "
        f"Score {analysis.get('investment_score', 0)}/100"
    )

    notification_svc.send_deal_alert(
        to_email=user_email,
        subject=subject,
        property_data={
            "address": prop.address,
            "city": prop.city,
            "state": prop.state,
            "zip_code": prop.zip_code,
            "price": prop.price,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "sqft": prop.sqft,
            "estimated_rent": prop.estimated_rent,
        },
        analysis=analysis,
        alert_name=alert_name,
    )

    logger.info(
        "Deal alert sent to %s for property %s (score: %d)",
        user_email,
        prop.address,
        analysis.get("investment_score", 0),
    )


# ---------------------------------------------------------------------------
# Database interface stubs
# ---------------------------------------------------------------------------


def _load_property(property_id: str):
    """Load property from database."""
    from app.ai.deal_analyzer import PropertyData
    logger.debug("Loading property %s for analysis", property_id)
    return None  # Placeholder


def _load_market_data(city: str, state: str):
    """Load market data for a city/state."""
    from app.ai.deal_analyzer import MarketData
    logger.debug("Loading market data for %s, %s", city, state)
    return MarketData(city=city, state=state)  # Placeholder


def _load_comparable_sales(property_data):
    """Load comparable sales within radius of property."""
    logger.debug("Loading comps for %s", property_data.address)
    return []  # Placeholder


def _store_analysis(property_id: str, analysis: dict) -> None:
    """Store analysis results in database."""
    logger.debug("Storing analysis for %s", property_id)


def _update_property_score(property_id: str, score: int, estimated_rent: float) -> None:
    """Update the investment score on the property record."""
    logger.debug("Updating score for %s: %d", property_id, score)


def _load_active_alerts() -> list[dict]:
    """Load all active user alerts."""
    return []


def _load_recently_analyzed_properties(minutes: int = 30) -> list:
    """Load properties analyzed in the last N minutes with their analysis."""
    return []


def _load_recently_updated_markets(hours: int = 24) -> list[dict]:
    """Load markets that have had data updates in the last N hours."""
    return []


def _load_market_properties_with_analysis(city: str, state: str) -> list:
    """Load properties and their current scores for a market."""
    return []
