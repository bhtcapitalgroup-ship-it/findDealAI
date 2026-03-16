"""
RealDeal AI - Market Analysis Engine

Scores and ranks real estate markets based on growth indicators, affordability,
rent ratios, migration trends, and economic fundamentals.
"""

import logging
from typing import Any

import anthropic

from app.ai.deal_analyzer import MarketData

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Evaluate and rank real estate markets for investment potential."""

    def __init__(self, anthropic_api_key: str | None = None):
        self._anthropic_key = anthropic_api_key

    # ------------------------------------------------------------------
    # Market Score (0-100)
    # ------------------------------------------------------------------

    def score_market(self, market_data: MarketData) -> int:
        """
        Score a market 0-100 based on:
            - Affordability / price-to-income          20 %
            - Rent-to-price ratio (gross yield)        20 %
            - Population growth                        15 %
            - Job growth                               15 %
            - Crime / safety                           10 %
            - School quality                            5 %
            - Inventory / supply                        5 %
            - Price appreciation trend                 10 %
        """
        scores: dict[str, float] = {}

        # Affordability: median_home_price / median_income  (lower = better)
        if market_data.median_income > 0:
            pti = market_data.median_home_price / market_data.median_income
            # 3x income = perfect; 8x = poor
            scores["affordability"] = max(0, min(1, (8 - pti) / 5)) * 20
        else:
            scores["affordability"] = 10  # neutral

        # Rent-to-price ratio (annual gross yield)
        if market_data.median_home_price > 0 and market_data.median_rent > 0:
            gross_yield = (market_data.median_rent * 12) / market_data.median_home_price
            # 1 % rule (12 % annual) = perfect
            scores["rent_ratio"] = max(0, min(1, gross_yield / 0.12)) * 20
        else:
            scores["rent_ratio"] = 0

        # Population growth: 2 %+ = excellent
        scores["pop_growth"] = max(0, min(1, market_data.population_growth_pct / 2.0)) * 15

        # Job growth: 3 %+ = excellent
        scores["job_growth"] = max(0, min(1, market_data.job_growth_pct / 3.0)) * 15

        # Crime: 0 = safest, 100 = worst
        scores["crime"] = max(0, min(1, (100 - market_data.crime_index) / 100)) * 10

        # Schools
        scores["schools"] = max(0, min(1, market_data.school_rating / 10)) * 5

        # Inventory: < 2 months = hot (seller's); > 6 = cold (buyer's)
        # Moderate inventory (3-4 months) is best for investors
        inv = market_data.inventory_months
        if inv <= 0:
            scores["inventory"] = 2.5
        elif inv < 2:
            scores["inventory"] = 3.0  # very hot, hard to find deals
        elif inv <= 4:
            scores["inventory"] = 5.0  # sweet spot
        elif inv <= 6:
            scores["inventory"] = 3.5
        else:
            scores["inventory"] = 1.5  # too much supply, prices may drop

        # Price trend YoY
        trend = market_data.price_trend_yoy_pct
        scores["price_trend"] = max(0, min(1, trend / 5.0)) * 10

        total = sum(scores.values())
        result = max(0, min(100, round(total)))

        logger.info(
            "Market score for %s, %s: %d (breakdown: %s)",
            market_data.city,
            market_data.state,
            result,
            {k: round(v, 1) for k, v in scores.items()},
        )
        return result

    # ------------------------------------------------------------------
    # Trending Markets
    # ------------------------------------------------------------------

    def identify_trending_markets(self, markets: list[MarketData]) -> list[dict[str, Any]]:
        """
        Identify and rank trending markets by momentum signals.

        Returns a sorted list of dicts with market info and scores,
        filtered to those showing positive momentum.
        """
        results: list[dict[str, Any]] = []

        for m in markets:
            momentum = self._calculate_momentum(m)
            overall_score = self.score_market(m)

            if momentum <= 0:
                continue

            results.append(
                {
                    "city": m.city,
                    "state": m.state,
                    "zip_code": m.zip_code,
                    "overall_score": overall_score,
                    "momentum_score": round(momentum, 2),
                    "population_growth": m.population_growth_pct,
                    "job_growth": m.job_growth_pct,
                    "price_trend_yoy": m.price_trend_yoy_pct,
                    "rent_trend_yoy": m.rent_trend_yoy_pct,
                    "median_home_price": m.median_home_price,
                    "median_rent": m.median_rent,
                    "net_migration": m.net_migration,
                }
            )

        results.sort(key=lambda x: x["momentum_score"], reverse=True)

        logger.info(
            "Identified %d trending markets out of %d total",
            len(results),
            len(markets),
        )
        return results

    # ------------------------------------------------------------------
    # Migration Score
    # ------------------------------------------------------------------

    def calculate_migration_score(self, market: MarketData) -> float:
        """
        Evaluate net migration impact on a 0-100 scale.

        Considers absolute net migration, migration rate (vs population),
        and correlated economic signals.
        """
        if market.population <= 0:
            return 50.0  # neutral

        migration_rate = market.net_migration / market.population

        # Absolute migration score: +10k/yr = very strong
        abs_score = min(1.0, max(-1.0, market.net_migration / 10_000))

        # Rate score: +1 % population growth from migration = very strong
        rate_score = min(1.0, max(-1.0, migration_rate / 0.01))

        # Economic correlation bonus
        econ_bonus = 0.0
        if market.job_growth_pct > 1.5:
            econ_bonus += 0.15
        if market.unemployment_rate < 4.0:
            econ_bonus += 0.10
        if market.median_income > 60_000:
            econ_bonus += 0.10

        raw = (abs_score * 0.4 + rate_score * 0.4 + econ_bonus) * 50 + 50
        result = round(max(0, min(100, raw)), 1)

        logger.info(
            "Migration score for %s, %s: %.1f (net: %+d, rate: %.3f%%)",
            market.city,
            market.state,
            result,
            market.net_migration,
            migration_rate * 100,
        )
        return result

    # ------------------------------------------------------------------
    # AI Market Report
    # ------------------------------------------------------------------

    def generate_market_report(self, market_data: MarketData) -> str:
        """Generate an AI-powered market narrative using Claude."""
        overall_score = self.score_market(market_data)
        migration_score = self.calculate_migration_score(market_data)

        prompt = f"""You are a real estate market analyst. Write a concise market report for investors.

Market: {market_data.city}, {market_data.state}
Overall Score: {overall_score}/100
Migration Score: {migration_score}/100

Key Metrics:
- Median Home Price: ${market_data.median_home_price:,.0f}
- Median Rent: ${market_data.median_rent:,.0f}/mo
- Price-to-Rent Ratio: {market_data.median_home_price / max(market_data.median_rent * 12, 1):.1f}x
- Population: {market_data.population:,}
- Population Growth: {market_data.population_growth_pct:.1f}%
- Job Growth: {market_data.job_growth_pct:.1f}%
- Unemployment: {market_data.unemployment_rate:.1f}%
- Median Income: ${market_data.median_income:,.0f}
- Crime Index: {market_data.crime_index:.0f}/100
- School Rating: {market_data.school_rating:.0f}/10
- Inventory: {market_data.inventory_months:.1f} months
- Price Trend (YoY): {market_data.price_trend_yoy_pct:+.1f}%
- Rent Trend (YoY): {market_data.rent_trend_yoy_pct:+.1f}%
- Net Migration: {market_data.net_migration:+,}

Write the report in this format:
## Market Overview
[2-3 sentences]

## Investment Thesis
[Bull case and bear case, 2-3 sentences each]

## Key Opportunities
- [opportunity 1]
- [opportunity 2]

## Risks
- [risk 1]
- [risk 2]

## Bottom Line
[1-2 sentence verdict for investors]
"""

        try:
            client = anthropic.Anthropic(api_key=self._anthropic_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            report = message.content[0].text
            logger.info("Market report generated for %s, %s", market_data.city, market_data.state)
            return report

        except Exception as exc:
            logger.error("Claude API failed for market report: %s", exc)
            return self._fallback_market_report(market_data, overall_score, migration_score)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_momentum(self, m: MarketData) -> float:
        """Composite momentum signal from growth indicators."""
        momentum = 0.0

        # Price appreciation momentum
        if m.price_trend_yoy_pct > 0:
            momentum += min(m.price_trend_yoy_pct, 10) * 2.0

        # Rent growth
        if m.rent_trend_yoy_pct > 0:
            momentum += min(m.rent_trend_yoy_pct, 8) * 1.5

        # Population growth
        momentum += max(0, m.population_growth_pct) * 5.0

        # Job growth
        momentum += max(0, m.job_growth_pct) * 4.0

        # Net migration signal
        if m.population > 0:
            migration_rate = m.net_migration / m.population
            momentum += max(0, migration_rate * 100) * 3.0

        # Tightening inventory = positive momentum
        if 0 < m.inventory_months < 3:
            momentum += (3 - m.inventory_months) * 2.0

        return momentum

    def _fallback_market_report(
        self, m: MarketData, score: int, migration: float
    ) -> str:
        if m.median_home_price > 0 and m.median_rent > 0:
            ptr = m.median_home_price / (m.median_rent * 12)
        else:
            ptr = 0

        if score >= 70:
            verdict = "This is a strong market for real estate investors."
        elif score >= 50:
            verdict = "This market shows moderate potential with selective opportunities."
        else:
            verdict = "Proceed with caution; fundamentals are below average for investors."

        return f"""## Market Overview
{m.city}, {m.state} has a median home price of ${m.median_home_price:,.0f} and \
median rent of ${m.median_rent:,.0f}/mo (price-to-rent ratio: {ptr:.1f}x). \
The market scores {score}/100 overall with a migration score of {migration:.0f}/100.

## Investment Thesis
**Bull case:** Job growth of {m.job_growth_pct:.1f}% and population growth of \
{m.population_growth_pct:.1f}% suggest increasing demand for housing. \
Net migration of {m.net_migration:+,} further supports rental demand.

**Bear case:** Crime index at {m.crime_index:.0f}/100 and school rating of \
{m.school_rating:.0f}/10 may limit appreciation in certain neighborhoods. \
Current inventory of {m.inventory_months:.1f} months \
{"indicates tight supply that may push prices higher" if m.inventory_months < 3 else "suggests balanced to loose supply"}.

## Key Opportunities
- {"Strong rent yields relative to home prices" if ptr < 15 else "Appreciation play in a growing market"}
- {"Population and job growth driving demand" if m.population_growth_pct > 0.5 else "Stable market with predictable returns"}

## Risks
- {"Rising prices may compress yields" if m.price_trend_yoy_pct > 5 else "Slow appreciation may limit equity growth"}
- {"Above-average crime may affect tenant quality" if m.crime_index > 50 else "Competition from other investors in desirable area"}

## Bottom Line
{verdict}
"""
