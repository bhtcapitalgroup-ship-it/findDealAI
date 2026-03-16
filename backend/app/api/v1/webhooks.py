"""Webhook handler endpoints for external services."""

import hashlib
import hmac
import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.conversation import (
    ChannelType,
    Conversation,
    ConversationStatus,
    Message,
    SenderType,
)
from app.models.payment import Payment, PaymentStatus
from app.models.tenant import Tenant
from app.schemas.webhooks import WebhookAck

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/twilio", response_model=WebhookAck)
async def twilio_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WebhookAck:
    """Handle inbound SMS from Twilio.

    Parses the incoming message, finds the tenant by phone number,
    and routes through the AI chat pipeline.
    """
    form_data = await request.form()
    from_number = form_data.get("From", "")
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")

    if not from_number or not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing From or Body in Twilio payload",
        )

    # Clean phone number (remove +1 prefix etc.)
    clean_phone = from_number.lstrip("+").lstrip("1") if from_number.startswith("+1") else from_number.lstrip("+")

    # Look up tenant by phone
    result = await db.execute(
        select(Tenant).where(Tenant.phone.contains(clean_phone))
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.warning("Inbound SMS from unknown number: %s", from_number)
        return WebhookAck(
            status="ignored",
            message="Tenant not found for this phone number",
        )

    # Find or create conversation for this tenant
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant.id,
            Conversation.channel == ChannelType.SMS,
            Conversation.status == ConversationStatus.OPEN,
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if conversation is None:
        conversation = Conversation(
            tenant_id=tenant.id,
            landlord_id=tenant.landlord_id,
            channel=ChannelType.SMS,
        )
        db.add(conversation)
        await db.flush()

    # Store the inbound message
    msg = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.TENANT,
        content=body,
        metadata_={"twilio_sid": message_sid, "from": from_number},
    )
    db.add(msg)

    # AI integration placeholder — will call chat_pipeline.process()
    # In production, this processes the message, generates a reply,
    # and sends it back via Twilio SMS API.
    ai_reply = (
        f"Hi {tenant.first_name}, we received your message. "
        f"A team member will follow up shortly."
    )

    ai_msg = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.AI,
        content=ai_reply,
        intent="general_inquiry",
        confidence=0.75,
    )
    db.add(ai_msg)
    await db.flush()

    return WebhookAck(status="ok", message="Message processed")


@router.post("/stripe", response_model=WebhookAck)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> WebhookAck:
    """Handle Stripe webhook events.

    Verifies the webhook signature and processes payment events.
    Currently handles: charge.succeeded, charge.failed, charge.refunded.
    """
    payload_bytes = await request.body()
    payload_str = payload_bytes.decode("utf-8")

    # Verify webhook signature
    if settings.STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            # Stripe signature verification pattern
            # In production, use stripe.Webhook.construct_event()
            elements = {
                el.split("=")[0]: el.split("=")[1]
                for el in stripe_signature.split(",")
                if "=" in el
            }
            timestamp = elements.get("t", "")
            signature = elements.get("v1", "")

            signed_payload = f"{timestamp}.{payload_str}"
            expected = hmac.new(
                settings.STRIPE_WEBHOOK_SECRET.encode(),
                signed_payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected, signature):
                logger.warning("Stripe webhook signature mismatch")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid webhook signature",
                )
        except (KeyError, ValueError) as exc:
            logger.warning("Stripe signature parse error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature format",
            )

    try:
        event = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "charge.succeeded":
        stripe_payment_id = data.get("id")
        if stripe_payment_id:
            result = await db.execute(
                select(Payment).where(
                    Payment.stripe_payment_id == stripe_payment_id
                )
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.COMPLETED
                payment.paid_date = date.today()
                await db.flush()
                logger.info("Payment %s marked completed via Stripe", payment.id)

    elif event_type == "charge.failed":
        stripe_payment_id = data.get("id")
        if stripe_payment_id:
            result = await db.execute(
                select(Payment).where(
                    Payment.stripe_payment_id == stripe_payment_id
                )
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.FAILED
                await db.flush()
                logger.info("Payment %s marked failed via Stripe", payment.id)

    elif event_type == "charge.refunded":
        stripe_payment_id = data.get("id")
        if stripe_payment_id:
            result = await db.execute(
                select(Payment).where(
                    Payment.stripe_payment_id == stripe_payment_id
                )
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.REFUNDED
                await db.flush()
                logger.info("Payment %s marked refunded via Stripe", payment.id)

    else:
        logger.info("Unhandled Stripe event type: %s", event_type)

    return WebhookAck(status="ok", message=f"Processed {event_type}")
