"""Contractor management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contractor import Contractor
from app.models.user import User
from app.schemas.contractor import ContractorCreate, ContractorResponse, ContractorUpdate

router = APIRouter(prefix="/contractors", tags=["contractors"])


@router.get("", response_model=list[ContractorResponse])
async def list_contractors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContractorResponse]:
    """List contractors for the current landlord."""
    stmt = (
        select(Contractor)
        .where(
            Contractor.landlord_id == current_user.id,
            Contractor.is_active == True,
        )
        .order_by(Contractor.company_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    contractors = result.scalars().all()
    return [ContractorResponse.model_validate(c) for c in contractors]


@router.post(
    "",
    response_model=ContractorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contractor(
    payload: ContractorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContractorResponse:
    """Add a new contractor."""
    contractor = Contractor(
        landlord_id=current_user.id,
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        phone=payload.phone,
        email=payload.email,
        trades=payload.trades,
    )
    db.add(contractor)
    await db.flush()
    await db.refresh(contractor)
    return ContractorResponse.model_validate(contractor)


@router.put("/{contractor_id}", response_model=ContractorResponse)
async def update_contractor(
    contractor_id: UUID,
    payload: ContractorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContractorResponse:
    """Update a contractor."""
    result = await db.execute(
        select(Contractor).where(
            Contractor.id == contractor_id,
            Contractor.is_active == True,
        )
    )
    contractor = result.scalar_one_or_none()

    if contractor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found",
        )
    if contractor.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this contractor",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contractor, field, value)

    await db.flush()
    await db.refresh(contractor)
    return ContractorResponse.model_validate(contractor)


@router.delete("/{contractor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contractor(
    contractor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a contractor (soft delete)."""
    result = await db.execute(
        select(Contractor).where(
            Contractor.id == contractor_id,
            Contractor.is_active == True,
        )
    )
    contractor = result.scalar_one_or_none()

    if contractor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found",
        )
    if contractor.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this contractor",
        )

    contractor.is_active = False
    await db.flush()
