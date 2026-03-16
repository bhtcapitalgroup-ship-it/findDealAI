"""Lease management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.lease import Lease
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus
from app.models.user import User
from app.schemas.lease import LeaseCreate, LeaseResponse, LeaseUpdate

router = APIRouter(prefix="/leases", tags=["leases"])


async def _verify_unit_ownership(
    unit_id: UUID, user: User, db: AsyncSession
) -> Unit:
    """Verify that the landlord owns the property containing the unit."""
    result = await db.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )
    prop_result = await db.execute(
        select(Property).where(Property.id == unit.property_id)
    )
    prop = prop_result.scalar_one_or_none()
    if prop is None or prop.landlord_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this unit",
        )
    return unit


async def _verify_tenant_ownership(
    tenant_id: UUID, user: User, db: AsyncSession
) -> Tenant:
    """Verify that the tenant belongs to the landlord."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    if tenant.landlord_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tenant",
        )
    return tenant


@router.get("", response_model=list[LeaseResponse])
async def list_leases(
    lease_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LeaseResponse]:
    """List leases, filterable by status.

    Only returns leases for units in properties owned by the current landlord.
    """
    stmt = (
        select(Lease)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.landlord_id == current_user.id)
    )

    if lease_status is not None:
        stmt = stmt.where(Lease.status == lease_status)

    stmt = stmt.order_by(Lease.start_date.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    leases = result.scalars().all()
    return [LeaseResponse.model_validate(l) for l in leases]


@router.post(
    "",
    response_model=LeaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lease(
    payload: LeaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeaseResponse:
    """Create a new lease linking a tenant to a unit."""
    unit = await _verify_unit_ownership(payload.unit_id, current_user, db)
    await _verify_tenant_ownership(payload.tenant_id, current_user, db)

    lease = Lease(
        unit_id=payload.unit_id,
        tenant_id=payload.tenant_id,
        rent_amount=payload.rent_amount,
        deposit_amount=payload.deposit_amount,
        start_date=payload.start_date,
        end_date=payload.end_date,
        rent_due_day=payload.rent_due_day,
        late_fee_amount=payload.late_fee_amount,
        late_fee_grace_days=payload.late_fee_grace_days,
        lease_type=payload.lease_type,
    )
    db.add(lease)

    # Mark unit as occupied
    unit.status = UnitStatus.OCCUPIED
    await db.flush()
    await db.refresh(lease)
    return LeaseResponse.model_validate(lease)


@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeaseResponse:
    """Get lease detail."""
    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    lease = result.scalar_one_or_none()

    if lease is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found"
        )

    # Verify ownership through unit -> property chain
    await _verify_unit_ownership(lease.unit_id, current_user, db)
    return LeaseResponse.model_validate(lease)


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: UUID,
    payload: LeaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeaseResponse:
    """Update a lease."""
    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    lease = result.scalar_one_or_none()

    if lease is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found"
        )

    await _verify_unit_ownership(lease.unit_id, current_user, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lease, field, value)

    # If lease is terminated, mark unit as vacant
    if payload.status == "terminated":
        unit_result = await db.execute(select(Unit).where(Unit.id == lease.unit_id))
        unit = unit_result.scalar_one_or_none()
        if unit:
            unit.status = UnitStatus.VACANT

    await db.flush()
    await db.refresh(lease)
    return LeaseResponse.model_validate(lease)
