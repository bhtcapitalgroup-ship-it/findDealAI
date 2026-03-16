"""Unit management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.property import Property
from app.models.unit import Unit
from app.models.user import User
from app.schemas.unit import UnitCreate, UnitResponse, UnitUpdate

router = APIRouter(tags=["units"])


async def _get_property_for_user(
    property_id: UUID, user: User, db: AsyncSession
) -> Property:
    """Fetch a property and verify ownership."""
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.is_active == True)
    )
    prop = result.scalar_one_or_none()
    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )
    if prop.landlord_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this property",
        )
    return prop


async def _get_unit_for_user(
    unit_id: UUID, user: User, db: AsyncSession
) -> Unit:
    """Fetch a unit and verify the landlord owns the parent property."""
    result = await db.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )
    # Verify property ownership
    await _get_property_for_user(unit.property_id, user, db)
    return unit


@router.get(
    "/properties/{property_id}/units",
    response_model=list[UnitResponse],
)
async def list_units(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UnitResponse]:
    """List all units for a property."""
    await _get_property_for_user(property_id, current_user, db)

    result = await db.execute(
        select(Unit)
        .where(Unit.property_id == property_id)
        .order_by(Unit.unit_number)
    )
    units = result.scalars().all()
    return [UnitResponse.model_validate(u) for u in units]


@router.post(
    "/properties/{property_id}/units",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    property_id: UUID,
    payload: UnitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitResponse:
    """Create a unit in a property."""
    await _get_property_for_user(property_id, current_user, db)

    unit = Unit(
        property_id=property_id,
        unit_number=payload.unit_number,
        bedrooms=payload.bedrooms,
        bathrooms=payload.bathrooms,
        sqft=payload.sqft,
        market_rent=payload.market_rent,
        status=payload.status,
    )
    db.add(unit)
    await db.flush()
    await db.refresh(unit)
    return UnitResponse.model_validate(unit)


@router.get("/units/{unit_id}", response_model=UnitResponse)
async def get_unit(
    unit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitResponse:
    """Get unit detail."""
    unit = await _get_unit_for_user(unit_id, current_user, db)
    return UnitResponse.model_validate(unit)


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: UUID,
    payload: UnitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnitResponse:
    """Update a unit."""
    unit = await _get_unit_for_user(unit_id, current_user, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(unit, field, value)

    await db.flush()
    await db.refresh(unit)
    return UnitResponse.model_validate(unit)
