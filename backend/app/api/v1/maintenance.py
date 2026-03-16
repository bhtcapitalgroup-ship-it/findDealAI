"""Maintenance request API endpoints."""

import uuid as uuid_mod
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.expense import Expense, ExpenseCategory
from app.models.maintenance import (
    MaintenancePhoto,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.models.quote import Quote, QuoteStatus
from app.models.user import User
from app.schemas.maintenance import (
    ApproveQuoteRequest,
    CompleteRequest,
    MaintenanceCreate,
    MaintenanceDetailResponse,
    MaintenanceResponse,
    MaintenanceUpdate,
)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("", response_model=list[MaintenanceResponse])
async def list_maintenance(
    maintenance_status: str | None = Query(None, alias="status"),
    urgency: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MaintenanceResponse]:
    """List maintenance requests, filterable by status and urgency."""
    stmt = select(MaintenanceRequest).where(
        MaintenanceRequest.landlord_id == current_user.id,
    )
    if maintenance_status is not None:
        stmt = stmt.where(MaintenanceRequest.status == maintenance_status)
    if urgency is not None:
        stmt = stmt.where(MaintenanceRequest.urgency == urgency)

    stmt = (
        stmt.order_by(MaintenanceRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    requests = result.scalars().all()
    return [MaintenanceResponse.model_validate(r) for r in requests]


@router.post(
    "",
    response_model=MaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_maintenance(
    payload: MaintenanceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Create a maintenance request, optionally with base64 photos."""
    req = MaintenanceRequest(
        unit_id=payload.unit_id,
        tenant_id=payload.tenant_id,
        landlord_id=current_user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        urgency=payload.urgency,
    )
    db.add(req)
    await db.flush()

    # Store photos if provided
    if payload.photos_base64:
        for i, photo_b64 in enumerate(payload.photos_base64):
            # S3 upload placeholder — would upload base64-decoded bytes to S3
            s3_key = f"maintenance/{req.id}/photo_{i}_{uuid_mod.uuid4().hex[:8]}.jpg"
            photo = MaintenancePhoto(
                request_id=req.id,
                s3_key=s3_key,
                uploaded_by="tenant",
            )
            db.add(photo)

    await db.flush()
    await db.refresh(req)
    return MaintenanceResponse.model_validate(req)


@router.get("/{request_id}", response_model=MaintenanceDetailResponse)
async def get_maintenance(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceDetailResponse:
    """Get maintenance request detail with photos and quotes."""
    stmt = (
        select(MaintenanceRequest)
        .options(
            selectinload(MaintenanceRequest.photos),
            selectinload(MaintenanceRequest.quotes),
        )
        .where(MaintenanceRequest.id == request_id)
    )
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    if req.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this request",
        )
    return MaintenanceDetailResponse.model_validate(req)


@router.put("/{request_id}", response_model=MaintenanceResponse)
async def update_maintenance(
    request_id: UUID,
    payload: MaintenanceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Update maintenance request status or details."""
    result = await db.execute(
        select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    if req.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this request",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(req, field, value)

    await db.flush()
    await db.refresh(req)
    return MaintenanceResponse.model_validate(req)


@router.post("/{request_id}/diagnose", response_model=MaintenanceResponse)
async def diagnose_maintenance(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Trigger AI photo diagnosis on a maintenance request.

    Analyzes uploaded photos to determine category, severity, and urgency.
    """
    result = await db.execute(
        select(MaintenanceRequest)
        .options(selectinload(MaintenanceRequest.photos))
        .where(MaintenanceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    if req.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to diagnose this request",
        )

    # AI integration placeholder — will call vision_diagnostics.diagnose()
    # In production, this sends the photo S3 keys to a vision model
    # and receives a structured diagnosis.
    photo_keys = [p.s3_key for p in req.photos]
    diagnosis = {
        "category": "plumbing",
        "severity": 3,
        "urgency": "urgent",
        "description": "Potential leak detected based on water damage patterns",
        "recommended_action": "Dispatch plumber within 24 hours",
        "photos_analyzed": len(photo_keys),
    }
    confidence = 0.85

    req.ai_diagnosis = diagnosis
    req.ai_confidence = confidence
    req.category = diagnosis["category"]
    req.urgency = diagnosis["urgency"]
    req.status = MaintenanceStatus.DIAGNOSED
    req.estimated_cost_low = 150.0
    req.estimated_cost_high = 450.0

    await db.flush()
    await db.refresh(req)
    return MaintenanceResponse.model_validate(req)


@router.post("/{request_id}/approve", response_model=MaintenanceResponse)
async def approve_quote(
    request_id: UUID,
    payload: ApproveQuoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Approve a quote for a maintenance request."""
    result = await db.execute(
        select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    if req.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to approve quotes for this request",
        )

    # Find and approve the quote
    quote_result = await db.execute(
        select(Quote).where(
            Quote.id == payload.quote_id,
            Quote.request_id == request_id,
        )
    )
    quote = quote_result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found for this request",
        )

    quote.status = QuoteStatus.ACCEPTED
    req.status = MaintenanceStatus.APPROVED

    # Reject other quotes for this request
    other_quotes_result = await db.execute(
        select(Quote).where(
            Quote.request_id == request_id,
            Quote.id != payload.quote_id,
            Quote.status == QuoteStatus.PENDING,
        )
    )
    for other_quote in other_quotes_result.scalars().all():
        other_quote.status = QuoteStatus.REJECTED

    await db.flush()
    await db.refresh(req)
    return MaintenanceResponse.model_validate(req)


@router.post("/{request_id}/complete", response_model=MaintenanceResponse)
async def complete_maintenance(
    request_id: UUID,
    payload: CompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Mark maintenance as complete and log the expense."""
    result = await db.execute(
        select(MaintenanceRequest)
        .options(selectinload(MaintenanceRequest.quotes))
        .where(MaintenanceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    if req.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this request",
        )

    req.status = MaintenanceStatus.COMPLETED
    req.actual_cost = payload.actual_cost
    req.completed_date = date.today()

    # Determine property_id through unit
    from app.models.unit import Unit
    unit_result = await db.execute(select(Unit).where(Unit.id == req.unit_id))
    unit = unit_result.scalar_one_or_none()
    property_id = unit.property_id if unit else None

    # Log the expense
    expense = Expense(
        landlord_id=current_user.id,
        property_id=property_id,
        maintenance_request_id=req.id,
        category=ExpenseCategory.MAINTENANCE,
        amount=payload.actual_cost,
        description=payload.notes or f"Maintenance: {req.title}",
        expense_date=date.today(),
    )
    db.add(expense)

    await db.flush()
    await db.refresh(req)
    return MaintenanceResponse.model_validate(req)
