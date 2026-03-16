"""
RealDeal AI - Core Deal Analysis Engine

Provides comprehensive real estate investment analysis including ARV estimation,
rehab cost projection, cash flow modeling, and AI-powered deal summaries.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

import anthropic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost tables
# ---------------------------------------------------------------------------
REHAB_COST_TABLE = {
    "kitchen": (15_000, 40_000),
    "bathroom": (8_000, 20_000),
    "roof": (8_000, 15_000),
    "hvac": (5_000, 12_000),
    "flooring_per_1000sqft": (3_000, 8_000),
    "paint": (2_000, 5_000),
    "windows": (3_000, 10_000),
    "foundation": (5_000, 15_000),
    "electrical": (3_000, 8_000),
    "plumbing": (4_000, 10_000),
    "landscaping": (2_000, 6_000),
    "driveway": (2_000, 5_000),
}

CONDITION_MULTIPLIERS = {
    "excellent": 0.0,
    "good": 0.15,
    "fair": 0.45,
    "poor": 0.75,
    "distressed": 1.0,
}

# Standard expense assumptions
VACANCY_RATE = 0.08
PROPERTY_MANAGEMENT_RATE = 0.10
MAINTENANCE_RATE = 0.05
CAPEX_RESERVE_RATE = 0.05
INSURANCE_ANNUAL_PER_100K = 600  # $600 per $100k of property value


@dataclass
class PropertyData:
    """Standardized property representation used across the platform."""

    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    price: float = 0.0
    bedrooms: int = 0
    bathrooms: float = 0.0
    sqft: int = 0
    lot_size_sqft: int = 0
    year_built: int = 2000
    property_type: str = "single_family"  # single_family, multi_family, condo, townhouse
    condition: str = "fair"  # excellent, good, fair, poor, distressed
    stories: int = 1
    garage: bool = False
    pool: bool = False
    hoa_monthly: float = 0.0
    tax_annual: float = 0.0
    estimated_rent: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    description: str = ""
    source: str = ""
    url: str = ""
    mls_id: str = ""
    days_on_market: int = 0
    num_units: int = 1
    extra: dict = field(default_factory=dict)


@dataclass
class MarketData:
    """Market-level statistics for a metro / zip code."""

    city: str = ""
    state: str = ""
    zip_code: str = ""
    median_home_price: float = 0.0
    median_rent: float = 0.0
    rent_per_sqft: float = 0.0
    price_per_sqft: float = 0.0
    population: int = 0
    population_growth_pct: float = 0.0
    job_growth_pct: float = 0.0
    unemployment_rate: float = 0.0
    median_income: float = 0.0
    crime_index: float = 50.0  # 0 = safest, 100 = most dangerous
    school_rating: float = 5.0  # 1-10
    avg_days_on_market: int = 30
    inventory_months: float = 3.0
    price_trend_yoy_pct: float = 0.0
    rent_trend_yoy_pct: float = 0.0
    net_migration: int = 0
    walkability_score: int = 50
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class CompSale:
    """A comparable sale used for ARV calculation."""

    address: str = ""
    sale_price: float = 0.0
    sqft: int = 0
    bedrooms: int = 0
    bathrooms: float = 0.0
    year_built: int = 2000
    condition: str = "good"
    distance_miles: float = 0.0
    days_since_sale: int = 0
    lot_size_sqft: int = 0


class DealAnalyzer:
    """
    Core analysis engine for evaluating real estate investment deals.

    Provides ARV estimation, rehab cost projection, rental analysis, cash flow
    modelling, BRRRR scoring, and an overall investment score (0-100).
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self._anthropic_key = anthropic_api_key

    # ------------------------------------------------------------------
    # ARV (After-Repair Value)
    # ------------------------------------------------------------------

    def calculate_arv(self, property: PropertyData, comps: list[CompSale]) -> float:
        """
        Estimate the After-Repair Value using comparable sales.

        Adjusts each comp's price-per-sqft for differences in size, age,
        bedrooms/bathrooms, condition, and distance.  Comps are weighted by
        recency and proximity.
        """
        if not comps:
            logger.warning("No comps provided for ARV; returning list price.")
            return property.price

        adjusted_prices: list[float] = []
        weights: list[float] = []

        for comp in comps:
            if comp.sqft <= 0:
                continue

            comp_ppsf = comp.sale_price / comp.sqft

            # --- Size adjustment: +-$2/sqft for every 10 % size difference ---
            size_diff_pct = (property.sqft - comp.sqft) / max(comp.sqft, 1)
            size_adj = -size_diff_pct * 2.0  # larger subject => lower ppsf adj

            # --- Bedroom / bathroom adjustment ---
            bed_adj = (property.bedrooms - comp.bedrooms) * 5_000
            bath_adj = (property.bathrooms - comp.bathrooms) * 3_000

            # --- Age adjustment: $500 per year newer ---
            age_adj = (property.year_built - comp.year_built) * 500

            # --- Condition adjustment ---
            cond_order = {"excellent": 4, "good": 3, "fair": 2, "poor": 1, "distressed": 0}
            # ARV assumes *repaired* condition = "good"
            cond_diff = cond_order.get("good", 3) - cond_order.get(comp.condition, 2)
            cond_adj = cond_diff * 8_000

            total_adj = bed_adj + bath_adj + age_adj + cond_adj
            adjusted_ppsf = comp_ppsf + size_adj
            adjusted_price = adjusted_ppsf * property.sqft + total_adj

            # --- Weight by recency (max 365 days) and proximity (max 3 mi) ---
            recency_w = max(0.1, 1.0 - comp.days_since_sale / 365)
            proximity_w = max(0.1, 1.0 - comp.distance_miles / 3.0)
            w = recency_w * proximity_w

            adjusted_prices.append(adjusted_price)
            weights.append(w)

        if not adjusted_prices:
            return property.price

        weighted_sum = sum(p * w for p, w in zip(adjusted_prices, weights))
        total_weight = sum(weights)
        arv = weighted_sum / total_weight

        logger.info("ARV calculated: $%,.0f from %d comps", arv, len(adjusted_prices))
        return round(arv, 2)

    # ------------------------------------------------------------------
    # Rehab Cost Estimation
    # ------------------------------------------------------------------

    def estimate_rehab_cost(self, property: PropertyData) -> tuple[float, float]:
        """
        Return (low, high) rehab estimates based on age, condition, and sqft.

        Older and worse-condition properties receive more line items and higher
        multipliers drawn from the detailed cost table.
        """
        condition = property.condition.lower()
        multiplier = CONDITION_MULTIPLIERS.get(condition, 0.45)

        if multiplier == 0.0:
            return (0.0, 0.0)

        age = max(0, 2026 - property.year_built)

        low_total = 0.0
        high_total = 0.0

        # Always included items
        always = ["paint", "flooring_per_1000sqft", "landscaping"]
        # Age-triggered items
        age_items: list[tuple[str, int]] = [
            ("roof", 20),
            ("hvac", 15),
            ("windows", 25),
            ("electrical", 30),
            ("plumbing", 30),
            ("foundation", 40),
        ]
        # Condition-triggered
        condition_items: list[tuple[str, str]] = [
            ("kitchen", "fair"),
            ("bathroom", "fair"),
            ("driveway", "poor"),
        ]

        cond_order = {"excellent": 4, "good": 3, "fair": 2, "poor": 1, "distressed": 0}
        prop_cond_rank = cond_order.get(condition, 2)

        for item in always:
            low, high = REHAB_COST_TABLE[item]
            if item == "flooring_per_1000sqft":
                factor = property.sqft / 1000
                low *= factor
                high *= factor
            low_total += low * multiplier
            high_total += high * multiplier

        for item, age_threshold in age_items:
            if age >= age_threshold:
                low, high = REHAB_COST_TABLE[item]
                low_total += low * multiplier
                high_total += high * multiplier

        for item, trigger_cond in condition_items:
            trigger_rank = cond_order.get(trigger_cond, 2)
            if prop_cond_rank <= trigger_rank:
                low, high = REHAB_COST_TABLE[item]
                num = max(1, property.bathrooms) if item == "bathroom" else 1
                low_total += low * multiplier * num
                high_total += high * multiplier * num

        low_total = round(low_total, 2)
        high_total = round(high_total, 2)

        logger.info(
            "Rehab estimate for %s (%s condition, %d yr old): $%,.0f - $%,.0f",
            property.address,
            condition,
            age,
            low_total,
            high_total,
        )
        return (low_total, high_total)

    # ------------------------------------------------------------------
    # Rent Estimation
    # ------------------------------------------------------------------

    def estimate_rent(self, property: PropertyData, market_data: MarketData) -> float:
        """
        Estimate monthly rent using a blended approach of rent-per-sqft,
        bedroom count, and market median with location adjustments.
        """
        # Method 1: Market rent-per-sqft
        rppsf = market_data.rent_per_sqft if market_data.rent_per_sqft > 0 else 1.0
        rent_by_sqft = rppsf * property.sqft

        # Method 2: Bedroom-based estimate from market median
        base_rent = market_data.median_rent if market_data.median_rent > 0 else 1_200
        bedroom_factor = {0: 0.7, 1: 0.85, 2: 1.0, 3: 1.15, 4: 1.3, 5: 1.45}
        bf = bedroom_factor.get(property.bedrooms, 1.0 + (property.bedrooms - 3) * 0.15)
        rent_by_beds = base_rent * bf

        # Method 3: Bathroom premium
        bath_premium = max(0, (property.bathrooms - 1)) * 75

        # Blend methods (50 % sqft, 35 % bed-based, 15 % bath bump)
        blended = rent_by_sqft * 0.50 + rent_by_beds * 0.35 + (rent_by_sqft + bath_premium) * 0.15

        # Adjustments
        # School rating adjustment: +/- up to 8 %
        school_adj = (market_data.school_rating - 5) / 5 * 0.08
        # Crime adjustment: lower crime => higher rent tolerance
        crime_adj = (50 - market_data.crime_index) / 50 * 0.05
        # Garage adds ~$50-100
        garage_adj = 75 if property.garage else 0
        # Year built freshness
        age = max(0, 2026 - property.year_built)
        age_adj = max(-0.05, min(0.05, (20 - age) / 20 * 0.05))

        blended *= 1 + school_adj + crime_adj + age_adj
        blended += garage_adj

        # Multi-unit: rent is per-unit already, multiply out then return per-unit
        estimated = round(max(blended, 400), 2)  # floor at $400

        logger.info("Estimated rent for %s: $%,.0f/mo", property.address, estimated)
        return estimated

    # ------------------------------------------------------------------
    # Financial Metrics
    # ------------------------------------------------------------------

    def _annual_insurance(self, property: PropertyData) -> float:
        return (property.price / 100_000) * INSURANCE_ANNUAL_PER_100K

    def _monthly_piti(
        self,
        property: PropertyData,
        down_payment_pct: float = 0.25,
        interest_rate: float = 0.07,
        loan_term: int = 30,
    ) -> float:
        """Principal + Interest + Taxes + Insurance (monthly)."""
        loan_amount = property.price * (1 - down_payment_pct)
        monthly_rate = interest_rate / 12
        num_payments = loan_term * 12

        if monthly_rate == 0:
            monthly_pi = loan_amount / num_payments
        else:
            monthly_pi = loan_amount * (
                monthly_rate * (1 + monthly_rate) ** num_payments
            ) / ((1 + monthly_rate) ** num_payments - 1)

        monthly_tax = property.tax_annual / 12
        monthly_insurance = self._annual_insurance(property) / 12
        monthly_hoa = property.hoa_monthly

        return monthly_pi + monthly_tax + monthly_insurance + monthly_hoa

    def calculate_cap_rate(self, property: PropertyData) -> float:
        """Cap Rate = NOI / Purchase Price."""
        if property.price <= 0:
            return 0.0

        gross_rent_annual = property.estimated_rent * 12 * property.num_units
        vacancy = gross_rent_annual * VACANCY_RATE
        egi = gross_rent_annual - vacancy  # Effective Gross Income

        operating_expenses = egi * (
            PROPERTY_MANAGEMENT_RATE + MAINTENANCE_RATE + CAPEX_RESERVE_RATE
        )
        tax_insurance = property.tax_annual + self._annual_insurance(property) + property.hoa_monthly * 12
        noi = egi - operating_expenses - tax_insurance

        cap_rate = noi / property.price
        logger.info("Cap rate for %s: %.2f%%", property.address, cap_rate * 100)
        return round(cap_rate, 4)

    def calculate_cash_flow(
        self,
        property: PropertyData,
        down_payment_pct: float = 0.25,
        interest_rate: float = 0.07,
        loan_term: int = 30,
    ) -> float:
        """Monthly cash flow after PITI, management, maintenance, vacancy, and capex."""
        gross_rent = property.estimated_rent * property.num_units
        vacancy = gross_rent * VACANCY_RATE
        egi = gross_rent - vacancy

        management = egi * PROPERTY_MANAGEMENT_RATE
        maintenance = egi * MAINTENANCE_RATE
        capex = egi * CAPEX_RESERVE_RATE

        piti = self._monthly_piti(property, down_payment_pct, interest_rate, loan_term)
        total_expenses = piti + management + maintenance + capex

        cash_flow = egi - total_expenses
        logger.info("Monthly cash flow for %s: $%,.0f", property.address, cash_flow)
        return round(cash_flow, 2)

    def calculate_cash_on_cash(
        self,
        property: PropertyData,
        down_payment_pct: float = 0.25,
    ) -> float:
        """Annual cash flow / total cash invested."""
        down_payment = property.price * down_payment_pct
        closing_costs = property.price * 0.03  # ~3 % closing
        total_cash = down_payment + closing_costs

        if total_cash <= 0:
            return 0.0

        annual_cf = self.calculate_cash_flow(property, down_payment_pct) * 12
        coc = annual_cf / total_cash
        logger.info("Cash-on-cash for %s: %.2f%%", property.address, coc * 100)
        return round(coc, 4)

    def calculate_dscr(self, property: PropertyData) -> float:
        """Debt Service Coverage Ratio = NOI / Annual Debt Service."""
        gross_rent_annual = property.estimated_rent * 12 * property.num_units
        vacancy = gross_rent_annual * VACANCY_RATE
        egi = gross_rent_annual - vacancy

        opex = egi * (PROPERTY_MANAGEMENT_RATE + MAINTENANCE_RATE + CAPEX_RESERVE_RATE)
        tax_insurance = property.tax_annual + self._annual_insurance(property) + property.hoa_monthly * 12
        noi = egi - opex - tax_insurance

        annual_debt_service = self._monthly_piti(property) * 12 - property.tax_annual - self._annual_insurance(property) - property.hoa_monthly * 12
        # debt service is P&I only for DSCR
        if annual_debt_service <= 0:
            return 0.0

        dscr = noi / annual_debt_service
        logger.info("DSCR for %s: %.2f", property.address, dscr)
        return round(dscr, 4)

    # ------------------------------------------------------------------
    # BRRRR Score
    # ------------------------------------------------------------------

    def calculate_brrrr_score(self, property: PropertyData) -> float:
        """
        Score 0-100 evaluating a property for the BRRRR strategy
        (Buy, Rehab, Rent, Refinance, Repeat).

        Components:
        - Equity capture potential (ARV vs purchase + rehab)  40 pts
        - Rent coverage (DSCR after refi)                     30 pts
        - Refinance potential (LTV headroom)                   20 pts
        - Market liquidity (days on market signal)             10 pts
        """
        rehab_low, rehab_high = self.estimate_rehab_cost(property)
        avg_rehab = (rehab_low + rehab_high) / 2
        all_in = property.price + avg_rehab

        # Rough ARV proxy when no comps: price / condition discount
        cond_discounts = {"excellent": 1.0, "good": 1.05, "fair": 1.15, "poor": 1.30, "distressed": 1.50}
        arv_est = property.price * cond_discounts.get(property.condition, 1.15)

        # Equity capture: target > 25 % equity after rehab
        equity_pct = (arv_est - all_in) / max(arv_est, 1)
        equity_score = min(40, max(0, equity_pct / 0.30 * 40))

        # Rent coverage via DSCR at 75 % LTV refi
        dscr = self.calculate_dscr(property)
        rent_score = min(30, max(0, (dscr - 0.8) / 0.7 * 30))

        # Refinance: can you pull all cash out at 75 % LTV?
        refi_amount = arv_est * 0.75
        cash_recoup_pct = refi_amount / max(all_in, 1)
        refi_score = min(20, max(0, cash_recoup_pct / 1.0 * 20))

        # Liquidity
        dom = property.days_on_market if property.days_on_market > 0 else 30
        liquidity_score = min(10, max(0, (90 - dom) / 90 * 10))

        total = equity_score + rent_score + refi_score + liquidity_score
        total = round(min(100, max(0, total)), 1)

        logger.info("BRRRR score for %s: %.1f", property.address, total)
        return total

    # ------------------------------------------------------------------
    # Investment Score (proprietary 0-100)
    # ------------------------------------------------------------------

    def calculate_investment_score(
        self, property: PropertyData, market_data: MarketData
    ) -> int:
        """
        Proprietary 0-100 investment score.

        Weights:
            Price vs ARV            25 %
            Rent / cash flow        20 %
            Crime level             10 %
            Population growth       10 %
            School ratings          10 %
            Job growth              10 %
            Market trend            10 %
            Property condition       5 %
        """
        scores: dict[str, float] = {}

        # 1. Price vs ARV (25 %)  -- use condition-based ARV proxy
        cond_discounts = {"excellent": 1.0, "good": 1.05, "fair": 1.15, "poor": 1.30, "distressed": 1.50}
        arv_proxy = property.price * cond_discounts.get(property.condition, 1.15)
        price_to_arv = property.price / max(arv_proxy, 1)
        # Best deal = buying at 70 % of ARV ("70 % rule")
        scores["price_arv"] = max(0, min(1, (1.0 - price_to_arv) / 0.30)) * 25

        # 2. Rent potential / cash flow (20 %)
        if property.estimated_rent > 0 and property.price > 0:
            rent_ratio = (property.estimated_rent * 12) / property.price  # gross yield
            # 1 % rule -> 12 % annual = excellent
            scores["rent_cf"] = max(0, min(1, rent_ratio / 0.12)) * 20
        else:
            scores["rent_cf"] = 0

        # 3. Crime level (10 %) -- lower = better
        scores["crime"] = max(0, min(1, (100 - market_data.crime_index) / 100)) * 10

        # 4. Population growth (10 %)
        # 2 %+ growth is excellent
        scores["pop_growth"] = max(0, min(1, market_data.population_growth_pct / 2.0)) * 10

        # 5. School ratings (10 %)
        scores["schools"] = max(0, min(1, market_data.school_rating / 10)) * 10

        # 6. Job growth (10 %)
        # 3 %+ is excellent
        scores["job_growth"] = max(0, min(1, market_data.job_growth_pct / 3.0)) * 10

        # 7. Market trend (10 %)
        # 5 %+ YoY price appreciation is excellent
        trend = market_data.price_trend_yoy_pct
        scores["market_trend"] = max(0, min(1, trend / 5.0)) * 10

        # 8. Property condition proxy (5 %)
        cond_scores = {"excellent": 1.0, "good": 0.8, "fair": 0.5, "poor": 0.25, "distressed": 0.1}
        scores["condition"] = cond_scores.get(property.condition, 0.5) * 5

        total = sum(scores.values())
        result = max(0, min(100, round(total)))

        logger.info(
            "Investment score for %s: %d (breakdown: %s)",
            property.address,
            result,
            {k: round(v, 1) for k, v in scores.items()},
        )
        return result

    # ------------------------------------------------------------------
    # AI Summary via Claude
    # ------------------------------------------------------------------

    def generate_ai_summary(
        self,
        property: PropertyData,
        analysis: dict[str, Any],
    ) -> str:
        """
        Generate a natural-language deal summary using Claude.

        Returns a structured summary with pros, cons, and recommendation.
        Falls back to a template-based summary if the API call fails.
        """
        prompt = self._build_summary_prompt(property, analysis)

        try:
            client = anthropic.Anthropic(api_key=self._anthropic_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = message.content[0].text
            logger.info("AI summary generated for %s", property.address)
            return summary

        except Exception as exc:
            logger.error("Claude API call failed, using template fallback: %s", exc)
            return self._fallback_summary(property, analysis)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_summary_prompt(self, prop: PropertyData, analysis: dict) -> str:
        return f"""You are an expert real estate investment analyst. Analyze this deal and provide a concise summary.

Property: {prop.address}, {prop.city}, {prop.state} {prop.zip_code}
Price: ${prop.price:,.0f}
Beds/Baths: {prop.bedrooms}/{prop.bathrooms}
Sqft: {prop.sqft:,}
Year Built: {prop.year_built}
Condition: {prop.condition}
Estimated Rent: ${prop.estimated_rent:,.0f}/mo

Analysis Results:
- Investment Score: {analysis.get('investment_score', 'N/A')}/100
- Cap Rate: {analysis.get('cap_rate', 0) * 100:.1f}%
- Monthly Cash Flow: ${analysis.get('cash_flow', 0):,.0f}
- Cash-on-Cash Return: {analysis.get('cash_on_cash', 0) * 100:.1f}%
- DSCR: {analysis.get('dscr', 0):.2f}
- BRRRR Score: {analysis.get('brrrr_score', 0):.0f}/100
- Estimated Rehab: ${analysis.get('rehab_low', 0):,.0f} - ${analysis.get('rehab_high', 0):,.0f}
- ARV: ${analysis.get('arv', 0):,.0f}

Provide your analysis in this exact format:
## Deal Summary
[2-3 sentence overview]

## Pros
- [pro 1]
- [pro 2]
- [pro 3]

## Cons
- [con 1]
- [con 2]

## Recommendation
[Buy / Hold for watching / Pass] - [1-2 sentence justification]
"""

    def _fallback_summary(self, prop: PropertyData, analysis: dict) -> str:
        score = analysis.get("investment_score", 0)
        cf = analysis.get("cash_flow", 0)
        cap = analysis.get("cap_rate", 0) * 100
        coc = analysis.get("cash_on_cash", 0) * 100

        if score >= 75:
            rec = "Strong Buy"
        elif score >= 60:
            rec = "Buy"
        elif score >= 45:
            rec = "Hold for watching"
        else:
            rec = "Pass"

        pros = []
        cons = []

        if cap >= 8:
            pros.append(f"Strong cap rate of {cap:.1f}%")
        elif cap < 5:
            cons.append(f"Low cap rate of {cap:.1f}%")

        if cf > 200:
            pros.append(f"Positive monthly cash flow of ${cf:,.0f}")
        elif cf < 0:
            cons.append(f"Negative cash flow of ${cf:,.0f}/mo")

        if coc > 10:
            pros.append(f"Excellent cash-on-cash return of {coc:.1f}%")
        elif coc < 5:
            cons.append(f"Low cash-on-cash return of {coc:.1f}%")

        if prop.condition in ("poor", "distressed"):
            cons.append("Property needs significant rehab")
        if prop.condition in ("excellent", "good"):
            pros.append("Property is in good condition, minimal rehab needed")

        if not pros:
            pros.append("Potential upside if market improves")
        if not cons:
            cons.append("No significant red flags identified")

        pros_str = "\n".join(f"- {p}" for p in pros)
        cons_str = "\n".join(f"- {c}" for c in cons)

        return f"""## Deal Summary
{prop.address}, {prop.city}, {prop.state} - Listed at ${prop.price:,.0f}. \
{prop.bedrooms}bd/{prop.bathrooms}ba, {prop.sqft:,} sqft built in {prop.year_built}. \
Investment score: {score}/100.

## Pros
{pros_str}

## Cons
{cons_str}

## Recommendation
{rec} - Score of {score}/100 with {cap:.1f}% cap rate and ${cf:,.0f}/mo cash flow.
"""
