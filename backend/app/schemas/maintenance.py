"""Pydantic schemas for maintenance."""

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MaintenanceCreate(BaseModel):
    """Schema for creating a maintenance request."""

    unit_id: UUID
    tenant_id: UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    category: Optional[str] = None
    urgency: str = "routine"
    photos_base64: Optional[List[str]] = None


class MaintenanceUpdate(BaseModel):
    """Schema for updating a maintenance request."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = None
    scheduled_date: Optional[date] = None


class MaintenancePhotoResponse(BaseModel):
    """Photo response."""

    id: UUID
    s3_key: str
    ai_analysis: Optional[dict[str, Any]] = None
    uploaded_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuoteResponse(BaseModel):
    """Quote response."""

    id: UUID
    request_id: UUID
    contractor_id: UUID
    amount: float
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    available_date: Optional[date] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceResponse(BaseModel):
    """Full maintenance request response."""

    id: UUID
    unit_id: UUID
    tenant_id: UUID
    landlord_id: UUID
    title: str
    description: str
    category: Optional[str] = None
    urgency: str
    status: str
    ai_diagnosis: Optional[dict[str, Any]] = None
    ai_confidence: Optional[float] = None
    estimated_cost_low: Optional[float] = None
    estimated_cost_high: Optional[float] = None
    actual_cost: Optional[float] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    tenant_rating: Optional[int] = None
    tenant_feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceDetailResponse(MaintenanceResponse):
    """Maintenance with photos and quotes."""

    photos: List[MaintenancePhotoResponse] = []
    quotes: List[QuoteResponse] = []


class ApproveQuoteRequest(BaseModel):
    """Request to approve a quote."""

    quote_id: UUID


class CompleteRequest(BaseModel):
    """Request to mark maintenance complete."""

    actual_cost: float = Field(..., gt=0)
    notes: Optional[str] = None
