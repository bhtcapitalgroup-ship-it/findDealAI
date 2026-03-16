"""Pydantic schemas for webhook payloads."""

from typing import Any, Optional

from pydantic import BaseModel


class TwilioInbound(BaseModel):
    """Twilio inbound SMS payload fields."""

    From: str
    To: str
    Body: str
    MessageSid: Optional[str] = None
    NumMedia: Optional[str] = None


class WebhookAck(BaseModel):
    """Generic webhook acknowledgment."""

    status: str = "ok"
    message: str = ""
