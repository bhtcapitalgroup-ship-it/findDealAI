"""Pydantic schemas for property management."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    """Schema for creating a property."""

    name: str = Field(..., min_length=1, max_length=255)
    address_line1: str = Field(..., min_length=1, max_length=500)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=255)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., min_length=5, max_length=10)
    property_type: str = "sfh"
    total_units: int = Field(1, ge=1)
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    mortgage_payment: Optional[float] = None
    insurance_cost: Optional[float] = None
    tax_annual: Optional[float] = None


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line1: Optional[str] = Field(None, min_length=1, max_length=500)
    address_line2: Optional[str] = None
    city: Optional[str] = Field(None, min_length=1, max_length=255)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, min_length=5, max_length=10)
    property_type: Optional[str] = None
    total_units: Optional[int] = Field(None, ge=1)
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    mortgage_payment: Optional[float] = None
    insurance_cost: Optional[float] = None
    tax_annual: Optional[float] = None


class UnitSummary(BaseModel):
    """Compact unit info for nesting in property responses."""

    id: UUID
    unit_number: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    market_rent: Optional[float] = None
    status: str

    model_config = {"from_attributes": True}


class PropertyResponse(BaseModel):
    """Full property detail response."""

    id: UUID
    landlord_id: UUID
    name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    property_type: str
    total_units: int
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    mortgage_payment: Optional[float] = None
    insurance_cost: Optional[float] = None
    tax_annual: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyDetailResponse(PropertyResponse):
    """Property response with embedded units."""

    units: List[UnitSummary] = []


class PropertyListResponse(BaseModel):
    """Paginated list of properties."""

    items: List[PropertyResponse]
    total: int
    page: int
    page_size: int


class PropertyFinancialSummary(BaseModel):
    """Financial summary for a property."""

    property_id: UUID
    property_name: str
    total_income: float
    total_expenses: float
    noi: float
    occupancy_rate: float
    total_units: int
    occupied_units: int
