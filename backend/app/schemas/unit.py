"""Pydantic schemas for units."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UnitCreate(BaseModel):
    """Schema for creating a unit."""

    unit_number: str = Field(..., min_length=1, max_length=50)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[float] = Field(None, ge=0)
    sqft: Optional[int] = Field(None, ge=0)
    market_rent: Optional[float] = Field(None, ge=0)
    status: str = "vacant"


class UnitUpdate(BaseModel):
    """Schema for updating a unit."""

    unit_number: Optional[str] = Field(None, min_length=1, max_length=50)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[float] = Field(None, ge=0)
    sqft: Optional[int] = Field(None, ge=0)
    market_rent: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None


class UnitResponse(BaseModel):
    """Full unit response."""

    id: UUID
    property_id: UUID
    unit_number: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    market_rent: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
