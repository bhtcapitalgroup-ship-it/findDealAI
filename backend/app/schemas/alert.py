"""Pydantic schemas for deal alerts."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertFilters(BaseModel):
    """Filter criteria stored inside an alert."""

    min_cap_rate: Optional[float] = None
    max_price: Optional[float] = None
    min_cash_flow: Optional[float] = None
    property_types: Optional[List[str]] = None
    states: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)


class AlertCreate(BaseModel):
    """Schema for creating an alert."""

    name: str = Field(..., min_length=1, max_length=255)
    filters: AlertFilters
    is_active: bool = True


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    filters: Optional[AlertFilters] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    """Schema for alert data returned to clients."""

    id: UUID
    user_id: UUID
    name: str
    filters: AlertFilters
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
