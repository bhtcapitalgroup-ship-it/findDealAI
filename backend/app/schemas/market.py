"""Pydantic schemas for market data."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class MarketDataResponse(BaseModel):
    """Full market data for a single zip code snapshot."""

    id: UUID
    zip_code: str
    city: str
    state: str
    metro_area: Optional[str] = None
    median_price: Optional[float] = None
    median_rent: Optional[float] = None
    price_growth_yoy: Optional[float] = None
    rent_growth_yoy: Optional[float] = None
    inventory_count: Optional[int] = None
    days_on_market_avg: Optional[float] = None
    population: Optional[int] = None
    population_growth: Optional[float] = None
    unemployment_rate: Optional[float] = None
    median_income: Optional[float] = None
    crime_index: Optional[float] = None
    school_rating_avg: Optional[float] = None
    migration_inflow: Optional[int] = None
    migration_outflow: Optional[int] = None
    snapshot_date: date

    model_config = {"from_attributes": True}


class HeatmapEntry(BaseModel):
    """Single zip code entry for the market heatmap."""

    zip_code: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    score: float
    median_price: Optional[float] = None
    median_rent: Optional[float] = None
    price_growth_yoy: Optional[float] = None
    rent_growth_yoy: Optional[float] = None


class MarketHeatmapResponse(BaseModel):
    """Market heatmap containing scored zip codes."""

    entries: List[HeatmapEntry]
    total: int


class TrendPoint(BaseModel):
    """Single data point in a time series."""

    date: date
    value: float


class MarketTrendResponse(BaseModel):
    """Time-series trend data for a market."""

    zip_code: str
    city: str
    state: str
    metric: str
    data_points: List[TrendPoint]
