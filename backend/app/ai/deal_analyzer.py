"""
RealDeal AI - Core Deal Analysis Engine

Provides comprehensive real estate investment analysis including ARV estimation,
rehab cost projection, cash flow modeling, and AI-powered deal summaries.

Two AI modes:
  Mode 1 (default): Pure math + template-based summaries (NO paid API needed)
  Mode 2 (optional): Local Ollama (Llama 3) for richer summaries if OLLAMA_URL is set
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp

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
    property_type: str = (
        "single_family"  # single_family, multi_family, condo, townhouse
    )
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

    AI Summary modes:
      - Default: Template-based summary using calculated metrics (FREE, no API)
      - Optional: Ollama local LLM for richer summaries (set OLLAMA_URL env var)
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ):
        self._ollama_url = ollama_url or os.getenv("OLLAMA_URL", "")
        self._ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "llama3")

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
            cond_order = {
                "excellent": 4,
                "good": 3,
                "fair": 2,
                "poor": 1,
                "distressed": 0,
            }
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
        blended = (
            rent_by_sqft * 0.50
            + rent_by_beds * 0.35
            + (rent_by_sqft + bath_premium) * 0.15
        )

        # Adjustments
        school_adj = (market_data.school_rating - 5) / 5 * 0.08
        crime_adj = (50 - market_data.crime_index) / 50 * 0.05
        garage_adj = 75 if property.garage else 0
        age = max(0, 2026 - property.year_built)
        age_adj = max(-0.05, min(0.05, (20 - age) / 20 * 0.05))

        blended *= 1 + school_adj + crime_adj + age_adj
        blended += garage_adj

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
            monthly_pi = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )

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
        tax_insurance = (
            property.tax_annual
            + self._annual_insurance(property)
            + property.hoa_monthly * 12
        )
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
        tax_insurance = (
            property.tax_annual
            + self._annual_insurance(property)
            + property.hoa_monthly * 12
        )
        noi = egi - opex - tax_insurance

        annual_debt_service = (
            self._monthly_piti(property) * 12
            - property.tax_annual
            - self._annual_insurance(property)
            - property.hoa_monthly * 12
        )
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
        """
        rehab_low, rehab_high = self.estimate_rehab_cost(property)
        avg_rehab = (rehab_low + rehab_high) / 2
        all_in = property.price + avg_rehab

        cond_discounts = {
            "excellent": 1.0,
            "good": 1.05,
            "fair": 1.15,
            "poor": 1.30,
            "distressed": 1.50,
        }
        arv_est = property.price * cond_discounts.get(property.condition, 1.15)

        equity_pct = (arv_est - all_in) / max(arv_est, 1)
        equity_score = min(40, max(0, equity_pct / 0.30 * 40))

        dscr = self.calculate_dscr(property)
        rent_score = min(30, max(0, (dscr - 0.8) / 0.7 * 30))

        refi_amount = arv_est * 0.75
        cash_recoup_pct = refi_amount / max(all_in, 1)
        refi_score = min(20, max(0, cash_recoup_pct / 1.0 * 20))

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

        cond_discounts = {
            "excellent": 1.0,
            "good": 1.05,
            "fair": 1.15,
            "poor": 1.30,
            "distressed": 1.50,
        }
        arv_proxy = property.price * cond_discounts.get(property.condition, 1.15)
        price_to_arv = property.price / max(arv_proxy, 1)
        scores["price_arv"] = max(0, min(1, (1.0 - price_to_arv) / 0.30)) * 25

        if property.estimated_rent > 0 and property.price > 0:
            rent_ratio = (property.estimated_rent * 12) / property.price
            scores["rent_cf"] = max(0, min(1, rent_ratio / 0.12)) * 20
        else:
            scores["rent_cf"] = 0

        scores["crime"] = max(0, min(1, (100 - market_data.crime_index) / 100)) * 10
        scores["pop_growth"] = (
            max(0, min(1, market_data.population_growth_pct / 2.0)) * 10
        )
        scores["schools"] = max(0, min(1, market_data.school_rating / 10)) * 10
        scores["job_growth"] = max(0, min(1, market_data.job_growth_pct / 3.0)) * 10

        trend = market_data.price_trend_yoy_pct
        scores["market_trend"] = max(0, min(1, trend / 5.0)) * 10

        cond_scores = {
            "excellent": 1.0,
            "good": 0.8,
            "fair": 0.5,
            "poor": 0.25,
            "distressed": 0.1,
        }
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
    # AI Summary -- Template-based (default) or Ollama (optional)
    # ------------------------------------------------------------------

    async def generate_ai_summary(
        self,
        property: PropertyData,
        analysis: dict[str, Any],
    ) -> str:
        """
        Generate a natural-language deal summary.

        Mode 1 (default): Template-based summary using calculated metrics.
                          No external API needed -- completely free.
        Mode 2 (optional): If OLLAMA_URL is set, use local Ollama for richer text.
                          Falls back to Mode 1 if Ollama is unavailable.
        """
        # Try Ollama first if configured
        if self._ollama_url:
            try:
                return await self._generate_ollama_summary(property, analysis)
            except Exception as exc:
                logger.warning(
                    "Ollama unavailable (%s), falling back to template summary", exc
                )

        # Default: template-based summary (always works, always free)
        return self._generate_template_summary(property, analysis)

    # ------------------------------------------------------------------
    # Mode 1: Template-based summary (FREE, no API)
    # ------------------------------------------------------------------

    def _generate_template_summary(
        self, prop: PropertyData, analysis: dict[str, Any]
    ) -> str:
        """
        Generate a detailed, template-based deal summary using actual metrics.

        Produces 4-5 specific pros/cons based on real calculated numbers.
        """
        score = analysis.get("investment_score", 0)
        cap_rate = analysis.get("cap_rate", 0)
        cap_pct = cap_rate * 100 if cap_rate < 1 else cap_rate
        cash_flow = analysis.get("cash_flow", 0)
        coc = analysis.get("cash_on_cash", 0)
        coc_pct = coc * 100 if coc < 1 else coc
        dscr = analysis.get("dscr", 0)
        brrrr = analysis.get("brrrr_score", 0)
        arv = analysis.get("arv", 0)
        rehab_low = analysis.get("rehab_low", 0)
        rehab_high = analysis.get("rehab_high", 0)

        # Determine rating
        if score >= 75:
            rating = "excellent"
            recommendation = "Strong Buy"
            rec_detail = (
                f"With an investment score of {score}/100, this property shows strong "
                f"fundamentals across all key metrics. The combination of "
                f"{'positive cash flow' if cash_flow > 0 else 'manageable expenses'} "
                f"and solid upside potential makes this a compelling acquisition target."
            )
        elif score >= 60:
            rating = "good"
            recommendation = "Buy"
            rec_detail = (
                f"Scoring {score}/100, this property offers a solid investment opportunity. "
                f"While not a home run, the numbers work and the risk-reward profile "
                f"is favorable for a buy-and-hold strategy."
            )
        elif score >= 45:
            rating = "moderate"
            recommendation = "Hold / Watch"
            rec_detail = (
                f"At {score}/100, this property is borderline. Consider negotiating "
                f"a lower price to improve returns, or watch for price reductions. "
                f"The deal could work at 5-10% below asking."
            )
        else:
            rating = "below average"
            recommendation = "Pass"
            rec_detail = (
                f"With a score of {score}/100, the numbers do not support this "
                f"investment at current pricing. The risk-adjusted returns are "
                f"insufficient to justify the capital outlay."
            )

        # Calculate upside percentage
        if arv > 0 and prop.price > 0:
            upside_pct = ((arv - prop.price) / prop.price) * 100
        else:
            upside_pct = 0

        # Property type display name
        type_names = {
            "single_family": "single-family home",
            "multi_family": "multi-family property",
            "condo": "condominium",
            "townhouse": "townhouse",
        }
        prop_type_display = type_names.get(prop.property_type, prop.property_type)

        # Build pros list (4-5 specific items)
        pros: list[str] = []
        cons: list[str] = []

        # Cap rate analysis
        if cap_pct >= 10:
            pros.append(
                f"Exceptional cap rate of {cap_pct:.1f}% -- well above the 8% "
                f"threshold that most investors target"
            )
        elif cap_pct >= 8:
            pros.append(
                f"Strong cap rate of {cap_pct:.1f}% indicates healthy income "
                f"relative to purchase price"
            )
        elif cap_pct >= 6:
            pros.append(
                f"Respectable cap rate of {cap_pct:.1f}% -- acceptable for "
                f"a market with appreciation potential"
            )
        elif cap_pct >= 4:
            cons.append(
                f"Cap rate of {cap_pct:.1f}% is below the 6% target; returns "
                f"depend on appreciation rather than cash flow"
            )
        else:
            cons.append(
                f"Very low cap rate of {cap_pct:.1f}% suggests this property "
                f"is overpriced relative to its income potential"
            )

        # Cash flow analysis
        if cash_flow >= 400:
            pros.append(
                f"Strong monthly cash flow of ${cash_flow:,.0f} provides a "
                f"comfortable buffer for unexpected expenses"
            )
        elif cash_flow >= 200:
            pros.append(
                f"Positive monthly cash flow of ${cash_flow:,.0f} after all "
                f"expenses including vacancy and capex reserves"
            )
        elif cash_flow >= 0:
            cons.append(
                f"Marginal cash flow of ${cash_flow:,.0f}/mo leaves little room "
                f"for unexpected repairs or extended vacancies"
            )
        else:
            cons.append(
                f"Negative cash flow of ${cash_flow:,.0f}/mo means this property "
                f"will require monthly out-of-pocket contributions"
            )

        # Cash-on-cash return
        if coc_pct >= 12:
            pros.append(
                f"Excellent {coc_pct:.1f}% cash-on-cash return significantly "
                f"outperforms stock market historical averages"
            )
        elif coc_pct >= 8:
            pros.append(
                f"Solid {coc_pct:.1f}% cash-on-cash return on invested capital"
            )
        elif coc_pct >= 4:
            cons.append(
                f"Cash-on-cash return of {coc_pct:.1f}% is modest -- consider "
                f"whether your capital could earn more elsewhere"
            )
        else:
            cons.append(
                f"Low cash-on-cash return of {coc_pct:.1f}% does not adequately "
                f"compensate for the illiquidity and effort of real estate"
            )

        # DSCR analysis
        if dscr >= 1.5:
            pros.append(
                f"DSCR of {dscr:.2f} provides excellent debt coverage -- lenders "
                f"will look favorably on this property"
            )
        elif dscr >= 1.25:
            pros.append(
                f"Healthy DSCR of {dscr:.2f} meets most lender requirements "
                f"for investment property financing"
            )
        elif dscr >= 1.0:
            cons.append(
                f"DSCR of {dscr:.2f} is tight -- any rent reduction or "
                f"unexpected expense could push debt coverage below 1.0"
            )
        elif dscr > 0:
            cons.append(
                f"DSCR of {dscr:.2f} is below 1.0, meaning rental income "
                f"does not fully cover debt service"
            )

        # Condition-based pros/cons
        if prop.condition in ("excellent", "good"):
            pros.append(
                f"Property is in {prop.condition} condition, minimizing immediate "
                f"rehab costs and reducing time-to-rent"
            )
        elif prop.condition == "fair":
            cons.append(
                f"Fair condition means estimated rehab of ${rehab_low:,.0f}-"
                f"${rehab_high:,.0f} before the property reaches full value"
            )
        elif prop.condition in ("poor", "distressed"):
            cons.append(
                f"Property in {prop.condition} condition requires significant "
                f"rehab investment of ${rehab_low:,.0f}-${rehab_high:,.0f}"
            )

        # ARV upside
        if upside_pct >= 20:
            pros.append(
                f"Estimated {upside_pct:.0f}% upside to ARV of ${arv:,.0f} "
                f"creates substantial forced equity opportunity"
            )
        elif upside_pct >= 10:
            pros.append(
                f"Moderate {upside_pct:.0f}% upside to estimated ARV of ${arv:,.0f}"
            )

        # BRRRR potential
        if brrrr >= 70:
            pros.append(
                f"BRRRR score of {brrrr:.0f}/100 makes this an excellent "
                f"candidate for the Buy-Rehab-Rent-Refinance-Repeat strategy"
            )
        elif brrrr < 40:
            cons.append(
                f"BRRRR score of {brrrr:.0f}/100 suggests limited potential "
                f"for the refinance-and-repeat strategy"
            )

        # Days on market signal
        if prop.days_on_market > 90:
            pros.append(
                f"Listed for {prop.days_on_market} days -- extended time on "
                f"market suggests seller motivation and negotiation leverage"
            )
        elif prop.days_on_market > 0 and prop.days_on_market < 7:
            cons.append(
                f"Only {prop.days_on_market} days on market -- limited time "
                f"for due diligence in a competitive situation"
            )

        # Ensure we have at least 2 of each
        if len(pros) < 2:
            pros.append("Potential upside if local market conditions improve")
        if len(cons) < 2:
            cons.append("No additional significant red flags identified at this time")

        # Cap at 5 each for readability
        pros = pros[:5]
        cons = cons[:5]

        pros_str = "\n".join(f"- {p}" for p in pros)
        cons_str = "\n".join(f"- {c}" for c in cons)

        return f"""## Deal Summary
This {prop_type_display} at {prop.address}, {prop.city}, {prop.state} {prop.zip_code} \
is listed at ${prop.price:,.0f} ({prop.bedrooms}bd/{prop.bathrooms}ba, {prop.sqft:,} sqft, \
built {prop.year_built}). \
{"The estimated ARV of $" + f"{arv:,.0f}" + f" represents {upside_pct:.0f}% upside from the current asking price. " if arv > 0 else ""}\
Monthly cash flow of ${cash_flow:,.0f} with a {cap_pct:.1f}% cap rate makes this \
a {rating} investment opportunity.

## Pros
{pros_str}

## Cons
{cons_str}

## Key Metrics
| Metric | Value | Rating |
|--------|-------|--------|
| Investment Score | {score}/100 | {"Good" if score >= 60 else "Fair" if score >= 45 else "Low"} |
| Cap Rate | {cap_pct:.1f}% | {"Good" if cap_pct >= 6 else "Low"} |
| Cash Flow | ${cash_flow:,.0f}/mo | {"Good" if cash_flow >= 200 else "Low"} |
| Cash-on-Cash | {coc_pct:.1f}% | {"Good" if coc_pct >= 8 else "Low"} |
| DSCR | {dscr:.2f} | {"Good" if dscr >= 1.25 else "Low"} |
| BRRRR Score | {brrrr:.0f}/100 | {"Good" if brrrr >= 60 else "Low"} |

## Recommendation
**{recommendation}** -- {rec_detail}
"""

    # ------------------------------------------------------------------
    # Mode 2: Ollama local LLM (optional, free)
    # ------------------------------------------------------------------

    async def _generate_ollama_summary(
        self, prop: PropertyData, analysis: dict[str, Any]
    ) -> str:
        """Generate a summary using local Ollama instance (Llama 3)."""
        prompt = self._build_ollama_prompt(prop, analysis)

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
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned status {resp.status}")
                data = await resp.json()
                summary = data.get("response", "")
                if not summary.strip():
                    raise RuntimeError("Ollama returned empty response")
                logger.info("Ollama summary generated for %s", prop.address)
                return summary

    def _build_ollama_prompt(self, prop: PropertyData, analysis: dict) -> str:
        cap_rate = analysis.get("cap_rate", 0)
        cap_pct = cap_rate * 100 if cap_rate < 1 else cap_rate
        coc = analysis.get("cash_on_cash", 0)
        coc_pct = coc * 100 if coc < 1 else coc

        return f"""You are an expert real estate investment analyst. Analyze this deal and provide a concise summary.

Property: {prop.address}, {prop.city}, {prop.state} {prop.zip_code}
Price: ${prop.price:,.0f}
Beds/Baths: {prop.bedrooms}/{prop.bathrooms}
Sqft: {prop.sqft:,}
Year Built: {prop.year_built}
Condition: {prop.condition}
Estimated Rent: ${prop.estimated_rent:,.0f}/mo

Analysis Results:
- Investment Score: {analysis.get("investment_score", "N/A")}/100
- Cap Rate: {cap_pct:.1f}%
- Monthly Cash Flow: ${analysis.get("cash_flow", 0):,.0f}
- Cash-on-Cash Return: {coc_pct:.1f}%
- DSCR: {analysis.get("dscr", 0):.2f}
- BRRRR Score: {analysis.get("brrrr_score", 0):.0f}/100
- Estimated Rehab: ${analysis.get("rehab_low", 0):,.0f} - ${analysis.get("rehab_high", 0):,.0f}
- ARV: ${analysis.get("arv", 0):,.0f}

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
