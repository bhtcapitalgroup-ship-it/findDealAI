"""Property management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.expense import Expense
from app.models.lease import Lease, LeaseStatus
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.unit import Unit, UnitStatus
from app.models.user import User
from app.schemas.property import (
    PropertyCreate,
    PropertyDetailResponse,
    PropertyFinancialSummary,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdate,
)

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyListResponse:
    """List all properties belonging to the current landlord."""
    base = select(Property).where(
        Property.landlord_id == current_user.id,
        Property.is_active == True,
    )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = base.order_by(Property.created_at.desc())
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    properties = result.scalars().all()

    return PropertyListResponse(
        items=[PropertyResponse.model_validate(p) for p in properties],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_property(
    payload: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Create a new property for the current landlord."""
    prop = Property(
        landlord_id=current_user.id,
        name=payload.name,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state.upper(),
        zip_code=payload.zip_code,
        property_type=payload.property_type,
        total_units=payload.total_units,
        purchase_price=payload.purchase_price,
        current_value=payload.current_value,
        mortgage_payment=payload.mortgage_payment,
        insurance_cost=payload.insurance_cost,
        tax_annual=payload.tax_annual,
    )
    db.add(prop)
    await db.flush()
    await db.refresh(prop)
    return PropertyResponse.model_validate(prop)


@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_property(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetailResponse:
    """Get property detail with its units."""
    stmt = (
        select(Property)
        .options(selectinload(Property.units))
        .where(Property.id == property_id, Property.is_active == True)
    )
    result = await db.execute(stmt)
    prop = result.scalar_one_or_none()

    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this property",
        )

    return PropertyDetailResponse.model_validate(prop)


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Update a property."""
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.is_active == True)
    )
    prop = result.scalar_one_or_none()

    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this property",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "state" and value is not None:
            value = value.upper()
        setattr(prop, field, value)

    await db.flush()
    await db.refresh(prop)
    return PropertyResponse.model_validate(prop)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a property (set is_active=False)."""
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.is_active == True)
    )
    prop = result.scalar_one_or_none()

    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this property",
        )

    prop.is_active = False
    await db.flush()


@router.get("/{property_id}/financials", response_model=PropertyFinancialSummary)
async def get_property_financials(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyFinancialSummary:
    """Get financial summary for a property: income - expenses = NOI."""
    result = await db.execute(
        select(Property)
        .options(selectinload(Property.units))
        .where(Property.id == property_id, Property.is_active == True)
    )
    prop = result.scalar_one_or_none()

    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this property",
        )

    # Total income: sum of completed payments for leases in this property's units
    unit_ids = [u.id for u in prop.units]
    total_income = 0.0
    if unit_ids:
        income_stmt = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.unit_id.in_(unit_ids),
                Payment.status == PaymentStatus.COMPLETED,
            )
        )
        total_income = float((await db.execute(income_stmt)).scalar_one())

    # Total expenses for this property
    expense_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.property_id == property_id,
        Expense.landlord_id == current_user.id,
    )
    total_expenses = float((await db.execute(expense_stmt)).scalar_one())

    # Occupancy
    total_units = len(unit_ids)
    occupied = sum(1 for u in prop.units if u.status == UnitStatus.OCCUPIED)

    noi = total_income - total_expenses
    occupancy_rate = (occupied / total_units * 100) if total_units > 0 else 0.0

    return PropertyFinancialSummary(
        property_id=prop.id,
        property_name=prop.name,
        total_income=total_income,
        total_expenses=total_expenses,
        noi=noi,
        occupancy_rate=occupancy_rate,
        total_units=total_units,
        occupied_units=occupied,
    )
