"""Saved deals API endpoints."""

import csv
import io
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.property import Property
from app.models.saved_deal import SavedDeal
from app.models.user import User
from app.schemas.deal import (
    DealComparison,
    DealComparisonItem,
    SavedDealCreate,
    SavedDealResponse,
    SavedDealUpdate,
)
from app.schemas.property import PropertyResponse

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("/save", response_model=SavedDealResponse, status_code=status.HTTP_201_CREATED)
async def save_deal(
    payload: SavedDealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedDealResponse:
    """Save a property as a deal for the current user.

    Optionally include custom ARV, rehab, and rent overrides.
    """
    # Verify property exists
    prop_result = await db.execute(
        select(Property).where(Property.id == payload.property_id)
    )
    if prop_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Check for duplicate
    dup = await db.execute(
        select(SavedDeal).where(
            SavedDeal.user_id == current_user.id,
            SavedDeal.property_id == payload.property_id,
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deal already saved",
        )

    deal = SavedDeal(
        user_id=current_user.id,
        property_id=payload.property_id,
        notes=payload.notes,
        custom_arv=payload.custom_arv,
        custom_rehab=payload.custom_rehab,
        custom_rent=payload.custom_rent,
        is_favorite=payload.is_favorite,
    )
    db.add(deal)
    await db.flush()
    await db.refresh(deal)
    return SavedDealResponse.model_validate(deal)


@router.get("/saved", response_model=List[SavedDealResponse])
async def list_saved_deals(
    favorites_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SavedDealResponse]:
    """List all saved deals for the current user.

    Optionally filter to favorites only.
    """
    stmt = select(SavedDeal).where(SavedDeal.user_id == current_user.id)
    if favorites_only:
        stmt = stmt.where(SavedDeal.is_favorite.is_(True))
    stmt = stmt.order_by(SavedDeal.created_at.desc())

    result = await db.execute(stmt)
    deals = result.scalars().all()
    return [SavedDealResponse.model_validate(d) for d in deals]


@router.put("/{deal_id}", response_model=SavedDealResponse)
async def update_deal(
    deal_id: UUID,
    payload: SavedDealUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedDealResponse:
    """Update a saved deal's notes, custom financials, or favorite status."""
    result = await db.execute(
        select(SavedDeal).where(
            SavedDeal.id == deal_id,
            SavedDeal.user_id == current_user.id,
        )
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved deal not found",
        )

    if payload.notes is not None:
        deal.notes = payload.notes
    if payload.custom_arv is not None:
        deal.custom_arv = payload.custom_arv
    if payload.custom_rehab is not None:
        deal.custom_rehab = payload.custom_rehab
    if payload.custom_rent is not None:
        deal.custom_rent = payload.custom_rent
    if payload.is_favorite is not None:
        deal.is_favorite = payload.is_favorite

    await db.flush()
    await db.refresh(deal)
    return SavedDealResponse.model_validate(deal)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a saved deal."""
    result = await db.execute(
        select(SavedDeal).where(
            SavedDeal.id == deal_id,
            SavedDeal.user_id == current_user.id,
        )
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved deal not found",
        )
    await db.delete(deal)


@router.post("/compare", response_model=DealComparison)
async def compare_deals(
    property_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealComparison:
    """Compare multiple properties side-by-side.

    Accepts a list of property IDs and returns a comparison including effective
    financials (using custom overrides from saved deals when available).
    """
    if len(property_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 property IDs are required for comparison",
        )
    if len(property_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 properties can be compared at once",
        )

    result = await db.execute(
        select(Property).where(Property.id.in_(property_ids))
    )
    properties = {p.id: p for p in result.scalars().all()}

    if len(properties) != len(property_ids):
        missing = set(property_ids) - set(properties.keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Properties not found: {[str(m) for m in missing]}",
        )

    # Fetch any saved deals for custom overrides
    saved_result = await db.execute(
        select(SavedDeal).where(
            SavedDeal.user_id == current_user.id,
            SavedDeal.property_id.in_(property_ids),
        )
    )
    saved_map = {sd.property_id: sd for sd in saved_result.scalars().all()}

    items: list[DealComparisonItem] = []
    best_cap: tuple[UUID | None, float] = (None, -float("inf"))
    best_cf: tuple[UUID | None, float] = (None, -float("inf"))
    best_score: tuple[UUID | None, float] = (None, -float("inf"))

    for pid in property_ids:
        prop = properties[pid]
        sd = saved_map.get(pid)

        eff_arv = float(sd.custom_arv) if sd and sd.custom_arv else (float(prop.arv_estimate) if prop.arv_estimate else None)
        eff_rehab = float(sd.custom_rehab) if sd and sd.custom_rehab else (float(prop.rehab_cost_low) if prop.rehab_cost_low else None)
        eff_rent = float(sd.custom_rent) if sd and sd.custom_rent else (float(prop.rent_estimate) if prop.rent_estimate else None)

        eff_cap = prop.cap_rate
        eff_cf = float(prop.cash_flow_monthly) if prop.cash_flow_monthly else None

        # Recompute cap rate and cash flow if custom rent is provided
        if eff_rent and prop.list_price and float(prop.list_price) > 0:
            annual_rent = eff_rent * 12
            expenses = (float(prop.monthly_taxes or 0) + float(prop.monthly_insurance or 0) + float(prop.hoa_monthly or 0)) * 12
            noi = annual_rent - expenses
            eff_cap = round(noi / float(prop.list_price) * 100, 2)
            eff_cf = round(eff_rent - float(prop.monthly_taxes or 0) - float(prop.monthly_insurance or 0) - float(prop.hoa_monthly or 0), 2)

        item = DealComparisonItem(
            property=PropertyResponse.model_validate(prop),
            custom_arv=float(sd.custom_arv) if sd and sd.custom_arv else None,
            custom_rehab=float(sd.custom_rehab) if sd and sd.custom_rehab else None,
            custom_rent=float(sd.custom_rent) if sd and sd.custom_rent else None,
            effective_arv=eff_arv,
            effective_rehab=eff_rehab,
            effective_rent=eff_rent,
            effective_cap_rate=eff_cap,
            effective_cash_flow=eff_cf,
        )
        items.append(item)

        if eff_cap is not None and eff_cap > best_cap[1]:
            best_cap = (prop.id, eff_cap)
        if eff_cf is not None and eff_cf > best_cf[1]:
            best_cf = (prop.id, eff_cf)
        score = prop.investment_score or 0
        if score > best_score[1]:
            best_score = (prop.id, score)

    return DealComparison(
        items=items,
        best_cap_rate_id=best_cap[0],
        best_cash_flow_id=best_cf[0],
        best_score_id=best_score[0],
    )


@router.get("/export")
async def export_deals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all saved deals for the current user as a CSV file."""
    result = await db.execute(
        select(SavedDeal)
        .where(SavedDeal.user_id == current_user.id)
        .order_by(SavedDeal.created_at.desc())
    )
    deals = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "address", "city", "state", "zip_code", "list_price",
        "bedrooms", "bathrooms", "sqft", "property_type",
        "cap_rate", "cash_flow_monthly", "investment_score",
        "arv_estimate", "rent_estimate",
        "custom_arv", "custom_rehab", "custom_rent",
        "notes", "is_favorite", "saved_at",
    ])

    for deal in deals:
        prop = deal.property
        writer.writerow([
            prop.address if prop else "",
            prop.city if prop else "",
            prop.state if prop else "",
            prop.zip_code if prop else "",
            float(prop.list_price) if prop and prop.list_price else "",
            prop.bedrooms if prop else "",
            prop.bathrooms if prop else "",
            prop.sqft if prop else "",
            prop.property_type.value if prop and prop.property_type else "",
            prop.cap_rate if prop else "",
            float(prop.cash_flow_monthly) if prop and prop.cash_flow_monthly else "",
            prop.investment_score if prop else "",
            float(prop.arv_estimate) if prop and prop.arv_estimate else "",
            float(prop.rent_estimate) if prop and prop.rent_estimate else "",
            float(deal.custom_arv) if deal.custom_arv else "",
            float(deal.custom_rehab) if deal.custom_rehab else "",
            float(deal.custom_rent) if deal.custom_rent else "",
            deal.notes or "",
            deal.is_favorite,
            deal.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=saved_deals.csv"},
    )
