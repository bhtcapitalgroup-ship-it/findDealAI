"""Pydantic schemas for conversations and messages."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    conversation_id: Optional[UUID] = None
    content: str = Field(..., min_length=1)
    sender_type: str = Field(..., pattern="^(tenant|ai|landlord)$")


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_type: str
    content: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    landlord_id: UUID
    channel: str
    status: str
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
