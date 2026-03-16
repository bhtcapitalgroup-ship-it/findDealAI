"""
Chrome Extension API — main analysis endpoint.

Receives scraped property data from the Zillow extension,
orchestrates data fetching, runs investment analysis, and
returns a unified response with metrics + AI verdict.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from app.ai.deal_analyzer import (
    DealAnalyzer,
    MarketData,
    PropertyData,
)
from app.core.config import settings
from app.schemas.extension import (
    AIVerdict,
    BRRRRAnalysis,
    ExtensionAnalyzeRequest,
    ExtensionAnalyzeResponse,
    FlipAnalysis,
    InvestmentMetrics,
    NeighborhoodData,
    RentComp,
    RentEstimateResponse,
)
from app.services.cache import cache_get, cache_set, TTL_VERDICT
from app.services.neighborhood import get_neighborhood_data
from app.services.rentcast import get_rent_comps, get_rent_estimate
from app.services.verdict import generate_verdict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/extension", tags=["extension"])

analyzer = DealAnalyzer(anthropic_api_key=settings.ANTHROPIC_API_KEY)


@router.post("/analyze", response_model=ExtensionAnalyzeResponse)
async def analyze_property(req: ExtensionAnalyzeRequest) -> ExtensionAnalyzeResponse:
    """
    Full property analysis for the Chrome extension.

    1. Fetch rent estimate + comps + neighborhood data in parallel
    2. Calculate investment metrics using DealAnalyzer
    3. Generate AI verdict
    4. Return unified response
    """
    if not req.price or req.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price is required and must be positive",
        )

    # Check full-analysis cache
    cache_key = f"ext_analysis:{req.zpid or req.address}"
    cached = await cache_get(cache_key)
    if cached:
        return ExtensionAnalyzeResponse(**cached)

    # --- Step 1: Parallel data fetching ---
    address = req.address or ""
    zip_code = req.zip_code or _extract_zip(address)

    rent_task = get_rent_estimate(
        address=address,
        beds=req.beds,
        baths=req.baths,
        sqft=req.sqft,
    )
    comps_task = get_rent_comps(
        address=address,
        beds=req.beds,
        baths=req.baths,
    )
    hood_task = get_neighborhood_data(
        zip_code=zip_code,
        latitude=req.latitude,
        longitude=req.longitude,
    ) if zip_code else asyncio.coroutine(lambda: {})()

    rent_raw, comps_raw, hood_raw = await asyncio.gather(
        rent_task, comps_task, hood_task,
        return_exceptions=True,
    )

    # Handle exceptions from gather
    if isinstance(rent_raw, Exception):
        logger.error("Rent fetch failed: %s", rent_raw)
        rent_raw = None
    if isinstance(comps_raw, Exception):
        logger.error("Comps fetch failed: %s", comps_raw)
        comps_raw = []
    if isinstance(hood_raw, Exception):
        logger.error("Neighborhood fetch failed: %s", hood_raw)
        hood_raw = {}

    # --- Step 2: Build rent estimate ---
    rent_amount = _resolve_rent(rent_raw, req)
    rent_confidence = _rent_confidence(rent_raw, comps_raw)

    comps_formatted = []
    if isinstance(comps_raw, list):
        for c in comps_raw[:5]:
            comps_formatted.append(RentComp(
                address=c.get("formattedAddress", c.get("address", "Unknown")),
                rent=c.get("price", c.get("rent", 0)),
                beds=c.get("bedrooms", 0),
                baths=c.get("bathrooms", 0),
                sqft=c.get("squareFootage", 0),
                distance_miles=c.get("distance", 0),
            ))

    rent_estimate = RentEstimateResponse(
        amount=rent_amount,
        confidence=rent_confidence,
        source="rentcast" if rent_raw else "estimated",
        comps=comps_formatted,
    )

    # --- Step 3: Calculate investment metrics ---
    prop_data = _to_property_data(req, rent_amount)
    market_data = _to_market_data(hood_raw if isinstance(hood_raw, dict) else {}, zip_code)

    cap_rate = analyzer.calculate_cap_rate(prop_data)
    cash_flow = analyzer.calculate_cash_flow(prop_data)
    coc = analyzer.calculate_cash_on_cash(prop_data)
    dscr = analyzer.calculate_dscr(prop_data)
    brrrr_score = analyzer.calculate_brrrr_score(prop_data)
    investment_score = analyzer.calculate_investment_score(prop_data, market_data)
    rehab_low, rehab_high = analyzer.estimate_rehab_cost(prop_data)

    # Mortgage calculation
    loan_amount = req.price * 0.75  # 25% down
    monthly_rate = 0.07 / 12
    num_payments = 360
    if monthly_rate > 0:
        monthly_mortgage = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** num_payments
        ) / ((1 + monthly_rate) ** num_payments - 1)
    else:
        monthly_mortgage = loan_amount / num_payments

    # NOI
    annual_rent = rent_amount * 12
    vacancy = annual_rent * 0.08
    egi = annual_rent - vacancy
    opex = egi * 0.20  # mgmt + maint + capex
    tax_ins = (prop_data.tax_annual + analyzer._annual_insurance(prop_data)
               + prop_data.hoa_monthly * 12)
    noi = egi - opex - tax_ins

    total_cash_invested = req.price * 0.25 + req.price * 0.03

    metrics = InvestmentMetrics(
        cap_rate=round(cap_rate * 100, 2),
        noi=round(noi),
        monthly_mortgage=round(monthly_mortgage),
        monthly_cash_flow=round(cash_flow),
        annual_cash_flow=round(cash_flow * 12),
        cash_on_cash=round(coc * 100, 2),
        total_cash_invested=round(total_cash_invested),
        dscr=round(dscr, 2),
    )

    # BRRRR
    arv = req.zestimate or req.price * 1.15
    refi_amount = arv * 0.75
    all_in = req.price + (rehab_low + rehab_high) / 2
    cash_left = max(0, all_in - refi_amount)

    if cash_left <= 0:
        brrrr_rating = "Excellent"
    elif cash_left / req.price < 0.1:
        brrrr_rating = "Good"
    elif cash_left / req.price < 0.2:
        brrrr_rating = "Fair"
    else:
        brrrr_rating = "Poor"

    brrrr = BRRRRAnalysis(
        arv=round(arv),
        rehab_low=round(rehab_low),
        rehab_high=round(rehab_high),
        refi_amount=round(refi_amount),
        cash_left_in_deal=round(cash_left),
        rating=brrrr_rating,
        score=brrrr_score,
    )

    # Flip
    holding_costs = (monthly_mortgage + prop_data.tax_annual / 12
                     + analyzer._annual_insurance(prop_data) / 12 + 200) * 6
    selling_costs = arv * 0.08
    avg_rehab = (rehab_low + rehab_high) / 2
    flip_profit = arv - req.price - avg_rehab - holding_costs - selling_costs
    flip_roi = (flip_profit / (req.price + avg_rehab)) * 100 if (req.price + avg_rehab) > 0 else 0

    if flip_roi > 25:
        flip_rating = "Excellent"
    elif flip_roi > 15:
        flip_rating = "Good"
    elif flip_roi > 5:
        flip_rating = "Marginal"
    else:
        flip_rating = "Avoid"

    flip = FlipAnalysis(
        arv=round(arv),
        rehab_low=round(rehab_low),
        rehab_high=round(rehab_high),
        holding_costs=round(holding_costs),
        selling_costs=round(selling_costs),
        profit=round(flip_profit),
        roi=round(flip_roi, 1),
        rating=flip_rating,
    )

    # --- Step 4: Neighborhood ---
    neighborhood = None
    if isinstance(hood_raw, dict) and hood_raw:
        neighborhood = NeighborhoodData(**{
            k: hood_raw[k] for k in NeighborhoodData.model_fields if k in hood_raw
        })

    # --- Step 5: AI Verdict ---
    verdict_dict = await generate_verdict(
        property_data=req.model_dump(),
        rent_estimate=rent_estimate.model_dump(),
        metrics={
            **metrics.model_dump(),
            "brrrr_score": brrrr_score,
            "brrrr_rating": brrrr_rating,
            "flip_roi": flip_roi,
            "flip_rating": flip_rating,
        },
        neighborhood=hood_raw if isinstance(hood_raw, dict) else None,
        investment_score=investment_score,
    )

    verdict = AIVerdict(**verdict_dict) if verdict_dict else None

    # --- Build response ---
    response = ExtensionAnalyzeResponse(
        property=req,
        rent_estimate=rent_estimate,
        metrics=metrics,
        brrrr=brrrr,
        flip=flip,
        neighborhood=neighborhood,
        verdict=verdict,
        investment_score=investment_score,
    )

    # Cache the full result
    await cache_set(cache_key, response.model_dump(), TTL_VERDICT)

    return response


# --- Helpers ---

def _resolve_rent(
    rent_raw: dict | None,
    req: ExtensionAnalyzeRequest,
) -> float:
    """Get rent from API response, or fall back to heuristic."""
    if rent_raw and isinstance(rent_raw, dict):
        rent = rent_raw.get("rent") or rent_raw.get("rentRangeMid")
        if rent and rent > 0:
            return float(rent)

    # Heuristic fallback: 0.8% of price (conservative 1% rule)
    if req.price:
        return round(req.price * 0.008, 2)
    return 0.0


def _rent_confidence(rent_raw: dict | None, comps_raw: list | None) -> float:
    """Estimate confidence in the rent figure."""
    if not rent_raw:
        return 30.0  # heuristic only

    base = 60.0
    # Boost for having comps
    if comps_raw and len(comps_raw) >= 3:
        base += 20.0
    elif comps_raw and len(comps_raw) >= 1:
        base += 10.0

    # Boost if Rentcast returned a tight range
    if isinstance(rent_raw, dict):
        low = rent_raw.get("rentRangeLow", 0)
        high = rent_raw.get("rentRangeHigh", 0)
        mid = rent_raw.get("rent", 0)
        if mid and high and low:
            spread = (high - low) / mid
            if spread < 0.15:
                base += 15.0
            elif spread < 0.30:
                base += 5.0

    return min(98.0, base)


def _to_property_data(req: ExtensionAnalyzeRequest, rent: float) -> PropertyData:
    """Convert extension request to DealAnalyzer's PropertyData."""
    return PropertyData(
        address=req.address or "",
        price=req.price or 0,
        bedrooms=req.beds or 0,
        bathrooms=req.baths or 0,
        sqft=req.sqft or 0,
        year_built=req.year_built or 2000,
        hoa_monthly=req.hoa or 0,
        estimated_rent=rent,
        latitude=req.latitude or 0,
        longitude=req.longitude or 0,
        condition="fair",  # default — we can't determine from Zillow scrape
        tax_annual=(req.price or 0) * 0.012,  # default 1.2% if not known
    )


def _to_market_data(hood: dict, zip_code: str) -> MarketData:
    """Convert neighborhood dict to DealAnalyzer's MarketData."""
    return MarketData(
        zip_code=zip_code,
        median_income=hood.get("median_income", 60000),
        population=hood.get("population", 0),
        population_growth_pct=hood.get("pop_growth", 0) or 0,
        crime_index=hood.get("crime_rate", 50),
        school_rating=hood.get("school_rating", 5),
        rent_trend_yoy_pct=hood.get("rent_growth", 0) or 0,
        unemployment_rate=hood.get("unemployment", 5),
        median_rent=hood.get("median_rent", 0) or 0,
    )


def _extract_zip(address: str) -> str:
    """Try to extract a 5-digit zip code from an address string."""
    import re
    match = re.search(r"\b(\d{5})\b", address)
    return match.group(1) if match else ""
