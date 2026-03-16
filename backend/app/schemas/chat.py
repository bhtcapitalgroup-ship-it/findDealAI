"""Pydantic schemas for AI chat and conversations."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Incoming chat message from a tenant."""

    tenant_id: UUID
    message: str = Field(..., min_length=1)
    channel: str = "web"
    attachment_base64: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """AI-generated response to a chat message."""

    conversation_id: UUID
    reply: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    escalated: bool = False
    actions_taken: List[str] = []


class MessageResponse(BaseModel):
    """Single message in a conversation."""

    id: UUID
    sender_type: str
    content: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Conversation with messages."""

    id: UUID
    tenant_id: UUID
    channel: str
    status: str
    messages: List[MessageResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class EscalationResponse(BaseModel):
    """Escalated conversation item."""

    id: UUID
    tenant_id: UUID
    tenant_name: str
    channel: str
    status: str
    last_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
