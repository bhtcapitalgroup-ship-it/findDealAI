"""Pydantic schemas for contractors."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ContractorCreate(BaseModel):
    """Schema for adding a contractor."""

    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = None
    trades: Optional[List[str]] = None


class ContractorUpdate(BaseModel):
    """Schema for updating a contractor."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = None
    trades: Optional[List[str]] = None


class ContractorResponse(BaseModel):
    """Full contractor response."""

    id: UUID
    landlord_id: UUID
    company_name: str
    contact_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    trades: Optional[List[str]] = None
    avg_rating: Optional[float] = None
    total_jobs: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("trades", mode="before")
    @classmethod
    def parse_trades(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v

    model_config = {"from_attributes": True}
