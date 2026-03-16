"""Payment management API endpoints."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit
from app.models.user import User
from app.schemas.payment import (
    AgingBucket,
    AgingReport,
    PaymentCreate,
    PaymentResponse,
    PaymentSummary,
)

router = APIRouter(prefix="/payments", tags=["payments"])


def _base_payment_query(user_id):
    """Base query that filters payments to landlord's tenants."""
    return (
        select(Payment)
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(Tenant.landlord_id == user_id)
    )


@router.get("/summary", response_model=PaymentSummary)
async def get_payment_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentSummary:
    """Collection summary: total collected, outstanding, and breakdown by status."""
    base = (
        select(Payment.status, func.coalesce(func.sum(Payment.amount), 0))
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(Tenant.landlord_id == current_user.id)
        .group_by(Payment.status)
    )
    result = await db.execute(base)
    rows = result.all()

    by_status: dict[str, float] = {}
    total_collected = 0.0
    total_outstanding = 0.0
    total_overdue = 0.0

    for payment_status, amount in rows:
        amount_f = float(amount)
        by_status[payment_status.value if hasattr(payment_status, 'value') else str(payment_status)] = amount_f
        if payment_status == PaymentStatus.COMPLETED:
            total_collected += amount_f
        elif payment_status == PaymentStatus.PENDING:
            total_outstanding += amount_f

    # Overdue: pending payments past due date
    overdue_stmt = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(
            Tenant.landlord_id == current_user.id,
            Payment.status == PaymentStatus.PENDING,
            Payment.due_date < date.today(),
        )
    )
    total_overdue = float((await db.execute(overdue_stmt)).scalar_one())

    return PaymentSummary(
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        total_overdue=total_overdue,
        by_status=by_status,
    )


@router.get("/aging", response_model=AgingReport)
async def get_aging_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgingReport:
    """Aging report grouping outstanding payments by days past due."""
    today = date.today()

    stmt = (
        select(Payment)
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(
            Tenant.landlord_id == current_user.id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()

    buckets_data = {
        "current": {"count": 0, "total": 0.0},
        "1-30": {"count": 0, "total": 0.0},
        "31-60": {"count": 0, "total": 0.0},
        "60+": {"count": 0, "total": 0.0},
    }

    total_outstanding = 0.0
    for p in payments:
        days_past = (today - p.due_date).days
        amount = float(p.amount)
        total_outstanding += amount

        if days_past <= 0:
            buckets_data["current"]["count"] += 1
            buckets_data["current"]["total"] += amount
        elif days_past <= 30:
            buckets_data["1-30"]["count"] += 1
            buckets_data["1-30"]["total"] += amount
        elif days_past <= 60:
            buckets_data["31-60"]["count"] += 1
            buckets_data["31-60"]["total"] += amount
        else:
            buckets_data["60+"]["count"] += 1
            buckets_data["60+"]["total"] += amount

    buckets = [
        AgingBucket(label=label, count=data["count"], total_amount=data["total"])
        for label, data in buckets_data.items()
    ]

    return AgingReport(buckets=buckets, total_outstanding=total_outstanding)


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    payment_status: str | None = Query(None, alias="status"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentResponse]:
    """List all payments, filterable by status and date range."""
    stmt = _base_payment_query(current_user.id)

    if payment_status is not None:
        stmt = stmt.where(Payment.status == payment_status)
    if start_date is not None:
        stmt = stmt.where(Payment.due_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Payment.due_date <= end_date)

    stmt = stmt.order_by(Payment.due_date.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    payments = result.scalars().all()
    return [PaymentResponse.model_validate(p) for p in payments]


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Record a payment."""
    # Verify tenant belongs to landlord
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == payload.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None or tenant.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to record payment for this tenant",
        )

    # Verify lease exists and belongs to the tenant
    lease_result = await db.execute(
        select(Lease).where(Lease.id == payload.lease_id)
    )
    lease = lease_result.scalar_one_or_none()
    if lease is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found"
        )
    if lease.tenant_id != payload.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lease does not belong to the specified tenant",
        )

    payment = Payment(
        lease_id=payload.lease_id,
        tenant_id=payload.tenant_id,
        amount=payload.amount,
        payment_type=payload.payment_type,
        payment_method=payload.payment_method,
        status=PaymentStatus.COMPLETED if payload.paid_date else PaymentStatus.PENDING,
        due_date=payload.due_date,
        paid_date=payload.paid_date,
        notes=payload.notes,
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return PaymentResponse.model_validate(payment)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Get payment detail."""
    result = await db.execute(
        select(Payment)
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(Payment.id == payment_id, Tenant.landlord_id == current_user.id)
    )
    payment = result.scalar_one_or_none()

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    return PaymentResponse.model_validate(payment)
