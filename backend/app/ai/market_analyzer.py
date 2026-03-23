"""
RealDeal AI - Market Analysis Engine

Scores and ranks real estate markets based on growth indicators, affordability,
rent ratios, migration trends, and economic fundamentals.

Two AI modes for market reports:
  Mode 1 (default): Template-based reports using calculated metrics (FREE)
  Mode 2 (optional): Local Ollama (Llama 3) for richer narrative (set OLLAMA_URL)
"""

import logging
import os
from typing import Any

import aiohttp

from app.ai.deal_analyzer import MarketData

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Evaluate and rank real estate markets for investment potential."""

    def __init__(
        self,
        ollama_url: str | None = None,
        ollama_model: str | None = None,
    ):
        self._ollama_url = ollama_url or os.getenv("OLLAMA_URL", "")
        self._ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "llama3")

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
            scores["affordability"] = max(0, min(1, (8 - pti) / 5)) * 20
        else:
            scores["affordability"] = 10  # neutral

        # Rent-to-price ratio (annual gross yield)
        if market_data.median_home_price > 0 and market_data.median_rent > 0:
            gross_yield = (market_data.median_rent * 12) / market_data.median_home_price
            scores["rent_ratio"] = max(0, min(1, gross_yield / 0.12)) * 20
        else:
            scores["rent_ratio"] = 0

        # Population growth: 2 %+ = excellent
        scores["pop_growth"] = (
            max(0, min(1, market_data.population_growth_pct / 2.0)) * 15
        )

        # Job growth: 3 %+ = excellent
        scores["job_growth"] = max(0, min(1, market_data.job_growth_pct / 3.0)) * 15

        # Crime: 0 = safest, 100 = worst
        scores["crime"] = max(0, min(1, (100 - market_data.crime_index) / 100)) * 10

        # Schools
        scores["schools"] = max(0, min(1, market_data.school_rating / 10)) * 5

        # Inventory: < 2 months = hot (seller's); > 6 = cold (buyer's)
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

    def identify_trending_markets(
        self, markets: list[MarketData]
    ) -> list[dict[str, Any]]:
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
        """
        if market.population <= 0:
            return 50.0  # neutral

        migration_rate = market.net_migration / market.population

        abs_score = min(1.0, max(-1.0, market.net_migration / 10_000))
        rate_score = min(1.0, max(-1.0, migration_rate / 0.01))

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
    # Market Report -- Template (default) or Ollama (optional)
    # ------------------------------------------------------------------

    async def generate_market_report(self, market_data: MarketData) -> str:
        """
        Generate a market report.

        Mode 1 (default): Template-based using calculated metrics (FREE).
        Mode 2 (optional): Ollama local LLM if OLLAMA_URL is configured.
        """
        overall_score = self.score_market(market_data)
        migration_score = self.calculate_migration_score(market_data)

        # Try Ollama if configured
        if self._ollama_url:
            try:
                return await self._generate_ollama_report(
                    market_data, overall_score, migration_score
                )
            except Exception as exc:
                logger.warning(
                    "Ollama unavailable (%s), falling back to template report", exc
                )

        # Default: template-based report (always works, always free)
        return self._generate_template_report(market_data, overall_score, migration_score)

    # ------------------------------------------------------------------
    # Mode 1: Template-based market report (FREE)
    # ------------------------------------------------------------------

    def _generate_template_report(
        self, m: MarketData, score: int, migration: float
    ) -> str:
        """Generate a detailed template-based market report with specific insights."""
        if m.median_home_price > 0 and m.median_rent > 0:
            ptr = m.median_home_price / (m.median_rent * 12)
            gross_yield = (m.median_rent * 12) / m.median_home_price * 100
        else:
            ptr = 0
            gross_yield = 0

        if m.median_income > 0:
            pti_ratio = m.median_home_price / m.median_income
        else:
            pti_ratio = 0

        # Market temperature
        if score >= 75:
            temp = "hot"
            verdict = (
                f"This is a strong market for real estate investors with a score of "
                f"{score}/100. Both cash flow and appreciation potential are above "
                f"average, making it suitable for buy-and-hold strategies."
            )
        elif score >= 60:
            temp = "warm"
            verdict = (
                f"Scoring {score}/100, {m.city} offers solid investment potential "
                f"with selective opportunities. Focus on properties that meet the "
                f"1% rule or offer value-add upside."
            )
        elif score >= 45:
            temp = "neutral"
            verdict = (
                f"At {score}/100, this is a mixed market. Deals exist but require "
                f"careful analysis. Consider this market for appreciation plays "
                f"rather than pure cash flow."
            )
        else:
            temp = "cool"
            verdict = (
                f"Scoring {score}/100, fundamentals are below average for investors. "
                f"Unless you have deep local knowledge and off-market deal flow, "
                f"consider higher-scoring markets."
            )

        # Build opportunities
        opportunities: list[str] = []
        risks: list[str] = []

        # Rent yield assessment
        if gross_yield >= 8:
            opportunities.append(
                f"Strong gross yield of {gross_yield:.1f}% (price-to-rent ratio "
                f"of {ptr:.1f}x) supports cash-flow-positive investments"
            )
        elif gross_yield >= 6:
            opportunities.append(
                f"Moderate gross yield of {gross_yield:.1f}% offers a balance "
                f"of cash flow and appreciation potential"
            )
        else:
            risks.append(
                f"Low gross yield of {gross_yield:.1f}% (PTR: {ptr:.1f}x) means "
                f"most properties will be negative cash flow without significant "
                f"down payments"
            )

        # Population and job growth
        if m.population_growth_pct > 1.0:
            opportunities.append(
                f"Strong population growth of {m.population_growth_pct:.1f}% annually "
                f"is driving housing demand and supporting rent increases"
            )
        elif m.population_growth_pct > 0:
            opportunities.append(
                f"Steady population growth of {m.population_growth_pct:.1f}% "
                f"provides a stable tenant pool"
            )
        else:
            risks.append(
                f"Population growth of {m.population_growth_pct:.1f}% signals "
                f"potential softening demand for housing"
            )

        if m.job_growth_pct > 2.0:
            opportunities.append(
                f"Exceptional job growth of {m.job_growth_pct:.1f}% is attracting "
                f"new residents and supporting rent growth of {m.rent_trend_yoy_pct:+.1f}% YoY"
            )
        elif m.job_growth_pct > 0.5:
            opportunities.append(
                f"Healthy job growth of {m.job_growth_pct:.1f}% with "
                f"unemployment at {m.unemployment_rate:.1f}%"
            )

        # Migration
        if migration >= 65:
            opportunities.append(
                f"Net migration of {m.net_migration:+,} people (migration score "
                f"{migration:.0f}/100) is a strong demand driver"
            )
        elif migration < 40:
            risks.append(
                f"Negative migration trends (score {migration:.0f}/100, net "
                f"{m.net_migration:+,}) may reduce rental demand over time"
            )

        # Price trend
        if m.price_trend_yoy_pct > 8:
            risks.append(
                f"Rapid price appreciation of {m.price_trend_yoy_pct:+.1f}% YoY "
                f"may signal overheating -- entry timing risk is elevated"
            )
        elif m.price_trend_yoy_pct > 3:
            opportunities.append(
                f"Healthy appreciation trend of {m.price_trend_yoy_pct:+.1f}% YoY "
                f"supports equity growth for buy-and-hold investors"
            )
        elif m.price_trend_yoy_pct < 0:
            risks.append(
                f"Declining prices ({m.price_trend_yoy_pct:+.1f}% YoY) create "
                f"risk of buying at the wrong time, but may offer below-market "
                f"entry points"
            )

        # Inventory
        if m.inventory_months < 2:
            risks.append(
                f"Very tight inventory ({m.inventory_months:.1f} months) makes "
                f"finding deals difficult -- strong competition from other buyers"
            )
        elif m.inventory_months > 6:
            opportunities.append(
                f"High inventory of {m.inventory_months:.1f} months gives buyers "
                f"negotiating leverage -- look for motivated sellers"
            )

        # Affordability
        if pti_ratio > 0:
            if pti_ratio < 4:
                opportunities.append(
                    f"Affordable market (price-to-income ratio of {pti_ratio:.1f}x) "
                    f"means a larger tenant pool can afford rents"
                )
            elif pti_ratio > 7:
                risks.append(
                    f"High price-to-income ratio of {pti_ratio:.1f}x may limit "
                    f"future appreciation and increase default risk"
                )

        # Crime
        if m.crime_index > 60:
            risks.append(
                f"Above-average crime index of {m.crime_index:.0f}/100 may affect "
                f"property values and tenant quality in certain neighborhoods"
            )
        elif m.crime_index < 30:
            opportunities.append(
                f"Low crime index of {m.crime_index:.0f}/100 makes the area "
                f"attractive to quality tenants and supports premium rents"
            )

        # Schools
        if m.school_rating >= 8:
            opportunities.append(
                f"Excellent school rating of {m.school_rating:.0f}/10 drives "
                f"family demand and supports higher property values"
            )

        # Ensure minimum items
        if len(opportunities) < 2:
            opportunities.append("Stable market fundamentals provide predictable returns")
        if len(risks) < 2:
            risks.append("General economic downturn could affect all real estate markets")

        opportunities = opportunities[:5]
        risks = risks[:5]

        opps_str = "\n".join(f"- {o}" for o in opportunities)
        risks_str = "\n".join(f"- {r}" for r in risks)

        # Bull and bear case
        bull_points = [o for o in opportunities[:2]]
        bear_points = [r for r in risks[:2]]

        bull_case = " ".join(bull_points) if bull_points else "Market stability provides a reliable base for investment."
        bear_case = " ".join(bear_points) if bear_points else "Limited upside potential in current conditions."

        return f"""## Market Overview
{m.city}, {m.state} is a {temp} market scoring {score}/100 overall. \
The median home price is ${m.median_home_price:,.0f} with median rents at \
${m.median_rent:,.0f}/mo, giving a price-to-rent ratio of {ptr:.1f}x \
(gross yield: {gross_yield:.1f}%). \
The market has a population of {m.population:,} with {m.population_growth_pct:.1f}% annual growth \
and a migration score of {migration:.0f}/100.

## Investment Thesis
**Bull case:** {bull_case}

**Bear case:** {bear_case}

## Key Metrics
| Metric | Value | Signal |
|--------|-------|--------|
| Median Home Price | ${m.median_home_price:,.0f} | {"Affordable" if pti_ratio < 5 else "Expensive"} |
| Median Rent | ${m.median_rent:,.0f}/mo | {"Strong" if gross_yield >= 7 else "Moderate"} |
| Gross Yield | {gross_yield:.1f}% | {"Good" if gross_yield >= 7 else "Low"} |
| Population Growth | {m.population_growth_pct:.1f}% | {"Strong" if m.population_growth_pct > 1 else "Moderate"} |
| Job Growth | {m.job_growth_pct:.1f}% | {"Strong" if m.job_growth_pct > 2 else "Moderate"} |
| Unemployment | {m.unemployment_rate:.1f}% | {"Low" if m.unemployment_rate < 4 else "High"} |
| Inventory | {m.inventory_months:.1f} months | {"Tight" if m.inventory_months < 3 else "Balanced" if m.inventory_months < 6 else "Loose"} |
| Price Trend (YoY) | {m.price_trend_yoy_pct:+.1f}% | {"Rising" if m.price_trend_yoy_pct > 0 else "Falling"} |
| Crime Index | {m.crime_index:.0f}/100 | {"Safe" if m.crime_index < 40 else "Average" if m.crime_index < 60 else "Elevated"} |
| School Rating | {m.school_rating:.0f}/10 | {"Good" if m.school_rating >= 7 else "Average"} |

## Key Opportunities
{opps_str}

## Risks
{risks_str}

## Bottom Line
{verdict}
"""

    # ------------------------------------------------------------------
    # Mode 2: Ollama local LLM (optional, free)
    # ------------------------------------------------------------------

    async def _generate_ollama_report(
        self, market_data: MarketData, overall_score: int, migration_score: float
    ) -> str:
        """Generate a market report using local Ollama instance."""
        if market_data.median_rent > 0:
            ptr = market_data.median_home_price / max(market_data.median_rent * 12, 1)
        else:
            ptr = 0

        prompt = f"""You are a real estate market analyst. Write a concise market report for investors.

Market: {market_data.city}, {market_data.state}
Overall Score: {overall_score}/100
Migration Score: {migration_score}/100

Key Metrics:
- Median Home Price: ${market_data.median_home_price:,.0f}
- Median Rent: ${market_data.median_rent:,.0f}/mo
- Price-to-Rent Ratio: {ptr:.1f}x
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

        url = f"{self._ollama_url.rstrip('/')}/api/generate"
        payload = {
            "model": self._ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 1024,
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned status {resp.status}")
                data = await resp.json()
                report = data.get("response", "")
                if not report.strip():
                    raise RuntimeError("Ollama returned empty response")
                logger.info(
                    "Ollama market report generated for %s, %s",
                    market_data.city,
                    market_data.state,
                )
                return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_momentum(self, m: MarketData) -> float:
        """Composite momentum signal from growth indicators."""
        momentum = 0.0

        if m.price_trend_yoy_pct > 0:
            momentum += min(m.price_trend_yoy_pct, 10) * 2.0

        if m.rent_trend_yoy_pct > 0:
            momentum += min(m.rent_trend_yoy_pct, 8) * 1.5

        momentum += max(0, m.population_growth_pct) * 5.0
        momentum += max(0, m.job_growth_pct) * 4.0

        if m.population > 0:
            migration_rate = m.net_migration / m.population
            momentum += max(0, migration_rate * 100) * 3.0

        if 0 < m.inventory_months < 3:
            momentum += (3 - m.inventory_months) * 2.0

        return momentum
