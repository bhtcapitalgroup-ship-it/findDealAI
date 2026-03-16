"""Market data API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.market import MarketData
from app.models.user import User
from app.schemas.market import (
    HeatmapEntry,
    MarketDataResponse,
    MarketHeatmapResponse,
    MarketTrendResponse,
    TrendPoint,
)

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/heatmap", response_model=MarketHeatmapResponse)
async def market_heatmap(
    state: Optional[str] = Query(None, description="Filter by state abbreviation"),
    min_score: float = Query(0, ge=0, le=100, description="Minimum composite score"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarketHeatmapResponse:
    """Return a heatmap of zip codes scored by investment attractiveness.

    The composite score is derived from rent growth, price growth, low crime,
    and high school ratings. Higher is better.
    """
    # Use the most recent snapshot per zip code via a subquery
    latest_sq = (
        select(
            MarketData.zip_code,
            func.max(MarketData.snapshot_date).label("max_date"),
        )
        .group_by(MarketData.zip_code)
        .subquery()
    )

    stmt = (
        select(MarketData)
        .join(
            latest_sq,
            (MarketData.zip_code == latest_sq.c.zip_code)
            & (MarketData.snapshot_date == latest_sq.c.max_date),
        )
    )

    if state:
        stmt = stmt.where(MarketData.state == state.upper())

    result = await db.execute(stmt)
    rows = result.scalars().all()

    entries: list[HeatmapEntry] = []
    for m in rows:
        # Composite score: weighted combination of available metrics
        score = 50.0  # baseline
        if m.rent_growth_yoy is not None:
            score += m.rent_growth_yoy * 3
        if m.price_growth_yoy is not None:
            score += m.price_growth_yoy * 2
        if m.school_rating_avg is not None:
            score += (m.school_rating_avg - 5) * 2
        if m.crime_index is not None:
            score -= (m.crime_index - 50) * 0.3
        if m.population_growth is not None:
            score += m.population_growth * 4
        score = max(0.0, min(100.0, score))

        if score < min_score:
            continue

        entries.append(
            HeatmapEntry(
                zip_code=m.zip_code,
                city=m.city,
                state=m.state,
                score=round(score, 1),
                median_price=float(m.median_price) if m.median_price else None,
                median_rent=float(m.median_rent) if m.median_rent else None,
                price_growth_yoy=m.price_growth_yoy,
                rent_growth_yoy=m.rent_growth_yoy,
            )
        )

    entries.sort(key=lambda e: e.score, reverse=True)
    entries = entries[:limit]

    return MarketHeatmapResponse(entries=entries, total=len(entries))


@router.get("/trending", response_model=List[MarketDataResponse])
async def trending_markets(
    metric: str = Query(
        "price_growth_yoy",
        description="Metric to rank by: price_growth_yoy, rent_growth_yoy, population_growth",
    ),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MarketDataResponse]:
    """Return the top trending markets ranked by the chosen metric."""
    column_map = {
        "price_growth_yoy": MarketData.price_growth_yoy,
        "rent_growth_yoy": MarketData.rent_growth_yoy,
        "population_growth": MarketData.population_growth,
    }
    col = column_map.get(metric)
    if col is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Choose from: {list(column_map.keys())}",
        )

    latest_sq = (
        select(
            MarketData.zip_code,
            func.max(MarketData.snapshot_date).label("max_date"),
        )
        .group_by(MarketData.zip_code)
        .subquery()
    )

    stmt = (
        select(MarketData)
        .join(
            latest_sq,
            (MarketData.zip_code == latest_sq.c.zip_code)
            & (MarketData.snapshot_date == latest_sq.c.max_date),
        )
        .where(col.isnot(None))
        .order_by(desc(col))
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [MarketDataResponse.model_validate(r) for r in rows]


@router.get("/compare", response_model=List[MarketDataResponse])
async def compare_markets(
    zip_codes: str = Query(
        ...,
        description="Comma-separated list of zip codes to compare",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MarketDataResponse]:
    """Compare market data across multiple zip codes.

    Provide a comma-separated list of zip codes to get the latest snapshot
    for each.
    """
    codes = [z.strip() for z in zip_codes.split(",") if z.strip()]
    if len(codes) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least 2 zip codes separated by commas",
        )
    if len(codes) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 zip codes can be compared at once",
        )

    latest_sq = (
        select(
            MarketData.zip_code,
            func.max(MarketData.snapshot_date).label("max_date"),
        )
        .where(MarketData.zip_code.in_(codes))
        .group_by(MarketData.zip_code)
        .subquery()
    )

    stmt = (
        select(MarketData)
        .join(
            latest_sq,
            (MarketData.zip_code == latest_sq.c.zip_code)
            & (MarketData.snapshot_date == latest_sq.c.max_date),
        )
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [MarketDataResponse.model_validate(r) for r in rows]


@router.get("/{zip_code}", response_model=MarketDataResponse)
async def get_market(
    zip_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarketDataResponse:
    """Retrieve the latest market data snapshot for a zip code."""
    result = await db.execute(
        select(MarketData)
        .where(MarketData.zip_code == zip_code)
        .order_by(desc(MarketData.snapshot_date))
        .limit(1)
    )
    market = result.scalar_one_or_none()
    if market is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for zip code {zip_code}",
        )
    return MarketDataResponse.model_validate(market)


@router.get("/{zip_code}/trends", response_model=MarketTrendResponse)
async def get_market_trends(
    zip_code: str,
    metric: str = Query(
        "median_price",
        description="Metric to trend: median_price, median_rent, price_growth_yoy, rent_growth_yoy",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarketTrendResponse:
    """Return historical trend data for a zip code and metric."""
    column_map = {
        "median_price": MarketData.median_price,
        "median_rent": MarketData.median_rent,
        "price_growth_yoy": MarketData.price_growth_yoy,
        "rent_growth_yoy": MarketData.rent_growth_yoy,
    }
    col = column_map.get(metric)
    if col is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Choose from: {list(column_map.keys())}",
        )

    result = await db.execute(
        select(MarketData)
        .where(MarketData.zip_code == zip_code, col.isnot(None))
        .order_by(MarketData.snapshot_date)
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trend data found for zip code {zip_code}",
        )

    data_points = [
        TrendPoint(date=r.snapshot_date, value=float(getattr(r, metric)))
        for r in rows
    ]

    return MarketTrendResponse(
        zip_code=zip_code,
        city=rows[0].city,
        state=rows[0].state,
        metric=metric,
        data_points=data_points,
    )
