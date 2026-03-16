"""Pydantic schemas for tenants."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TenantCreate(BaseModel):
    """Schema for creating a tenant."""

    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    preferred_language: str = "en"


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = None
    portal_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Full tenant response."""

    id: UUID
    landlord_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    portal_enabled: bool
    preferred_language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
