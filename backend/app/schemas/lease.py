"""Pydantic schemas for leases."""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LeaseCreate(BaseModel):
    """Schema for creating a lease."""

    unit_id: UUID
    tenant_id: UUID
    rent_amount: float = Field(..., gt=0)
    deposit_amount: Optional[float] = Field(None, ge=0)
    start_date: date
    end_date: Optional[date] = None
    rent_due_day: int = Field(1, ge=1, le=28)
    late_fee_amount: Optional[float] = Field(None, ge=0)
    late_fee_grace_days: int = Field(5, ge=0)
    lease_type: str = "fixed"


class LeaseUpdate(BaseModel):
    """Schema for updating a lease."""

    rent_amount: Optional[float] = Field(None, gt=0)
    deposit_amount: Optional[float] = Field(None, ge=0)
    end_date: Optional[date] = None
    rent_due_day: Optional[int] = Field(None, ge=1, le=28)
    late_fee_amount: Optional[float] = Field(None, ge=0)
    late_fee_grace_days: Optional[int] = Field(None, ge=0)
    lease_type: Optional[str] = None
    status: Optional[str] = None


class LeaseResponse(BaseModel):
    """Full lease response."""

    id: UUID
    unit_id: UUID
    tenant_id: UUID
    rent_amount: float
    deposit_amount: Optional[float] = None
    start_date: date
    end_date: Optional[date] = None
    rent_due_day: int
    late_fee_amount: Optional[float] = None
    late_fee_grace_days: int
    lease_type: str
    status: str
    document_id: Optional[UUID] = None
    ai_analysis: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
