"""Pydantic schemas for saved deals."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.property import PropertyResponse


class SavedDealCreate(BaseModel):
    """Schema for saving a deal."""

    property_id: UUID
    notes: Optional[str] = None
    custom_arv: Optional[float] = None
    custom_rehab: Optional[float] = None
    custom_rent: Optional[float] = None
    is_favorite: bool = False


class SavedDealUpdate(BaseModel):
    """Schema for updating a saved deal."""

    notes: Optional[str] = None
    custom_arv: Optional[float] = None
    custom_rehab: Optional[float] = None
    custom_rent: Optional[float] = None
    is_favorite: Optional[bool] = None


class SavedDealResponse(BaseModel):
    """Schema for a saved deal returned to clients."""

    id: UUID
    user_id: UUID
    property_id: UUID
    notes: Optional[str] = None
    custom_arv: Optional[float] = None
    custom_rehab: Optional[float] = None
    custom_rent: Optional[float] = None
    is_favorite: bool
    property: PropertyResponse
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealComparisonItem(BaseModel):
    """Single property in a side-by-side comparison."""

    property: PropertyResponse
    custom_arv: Optional[float] = None
    custom_rehab: Optional[float] = None
    custom_rent: Optional[float] = None
    effective_arv: Optional[float] = None
    effective_rehab: Optional[float] = None
    effective_rent: Optional[float] = None
    effective_cap_rate: Optional[float] = None
    effective_cash_flow: Optional[float] = None


class DealComparison(BaseModel):
    """Side-by-side comparison of multiple properties."""

    items: List[DealComparisonItem]
    best_cap_rate_id: Optional[UUID] = None
    best_cash_flow_id: Optional[UUID] = None
    best_score_id: Optional[UUID] = None
