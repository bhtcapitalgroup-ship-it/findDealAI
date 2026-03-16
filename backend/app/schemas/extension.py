"""Pydantic schemas for the Chrome extension API."""

from typing import Optional

from pydantic import BaseModel, Field


# --- Request ---

class ExtensionAnalyzeRequest(BaseModel):
    """Property data scraped from Zillow by the Chrome extension."""

    address: Optional[str] = None
    price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    year_built: Optional[int] = None
    property_type: Optional[str] = None
    hoa: Optional[float] = None
    zestimate: Optional[float] = None
    zpid: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# --- Response sub-models ---

class RentComp(BaseModel):
    address: str
    rent: float
    beds: int
    baths: float
    sqft: int
    distance_miles: float


class RentEstimateResponse(BaseModel):
    amount: float
    confidence: float = Field(description="0-100 confidence score")
    source: str = "rentcast"
    comps: list[RentComp] = []


class InvestmentMetrics(BaseModel):
    cap_rate: float
    noi: float
    monthly_mortgage: float
    monthly_cash_flow: float
    annual_cash_flow: float
    cash_on_cash: float
    total_cash_invested: float
    dscr: float


class BRRRRAnalysis(BaseModel):
    arv: float
    rehab_low: float
    rehab_high: float
    refi_amount: float
    cash_left_in_deal: float
    rating: str  # Excellent, Good, Fair, Poor
    score: float  # 0-100


class FlipAnalysis(BaseModel):
    arv: float
    rehab_low: float
    rehab_high: float
    holding_costs: float
    selling_costs: float
    profit: float
    roi: float
    rating: str  # Excellent, Good, Marginal, Avoid


class NeighborhoodData(BaseModel):
    crime_rate: Optional[float] = None  # 0-100 index
    crime_label: Optional[str] = None
    school_rating: Optional[float] = None  # 1-10
    pop_growth: Optional[float] = None  # percent per year
    rent_growth: Optional[float] = None  # percent per year
    median_income: Optional[float] = None
    unemployment: Optional[float] = None


class AIVerdict(BaseModel):
    verdict: str  # "Good Deal", "Average", "Avoid"
    confidence: str  # "High", "Medium", "Low"
    summary: str
    risks: list[str] = []
    opportunities: list[str] = []


# --- Full response ---

class ExtensionAnalyzeResponse(BaseModel):
    property: ExtensionAnalyzeRequest
    rent_estimate: RentEstimateResponse
    metrics: InvestmentMetrics
    brrrr: BRRRRAnalysis
    flip: FlipAnalysis
    neighborhood: Optional[NeighborhoodData] = None
    verdict: Optional[AIVerdict] = None
    investment_score: int = Field(ge=0, le=100)
