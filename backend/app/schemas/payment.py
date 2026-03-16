"""Pydantic schemas for payments."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Schema for recording a payment."""

    lease_id: UUID
    tenant_id: UUID
    amount: float = Field(..., gt=0)
    payment_type: str = "rent"
    payment_method: Optional[str] = None
    due_date: date
    paid_date: Optional[date] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    """Full payment response."""

    id: UUID
    lease_id: UUID
    tenant_id: UUID
    amount: float
    payment_type: str
    payment_method: Optional[str] = None
    status: str
    stripe_payment_id: Optional[str] = None
    due_date: date
    paid_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentSummary(BaseModel):
    """Collection summary."""

    total_collected: float
    total_outstanding: float
    total_overdue: float
    by_status: dict[str, float]


class AgingBucket(BaseModel):
    """Single aging bucket."""

    label: str
    count: int
    total_amount: float


class AgingReport(BaseModel):
    """Aging report with buckets."""

    buckets: List[AgingBucket]
    total_outstanding: float
