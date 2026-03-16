"""Notification Celery tasks: SMS, email, and in-app notifications."""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.notification import Notification, NotificationType
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Notification type mapping
# ---------------------------------------------------------------------------

CATEGORY_TYPE_MAP = {
    "payment_received": NotificationType.PAYMENT_RECEIVED,
    "payment_overdue": NotificationType.PAYMENT_OVERDUE,
    "maintenance_new": NotificationType.MAINTENANCE_NEW,
    "maintenance_update": NotificationType.MAINTENANCE_UPDATE,
    "lease_expiring": NotificationType.LEASE_EXPIRING,
    "escalation": NotificationType.ESCALATION,
    "system": NotificationType.SYSTEM,
}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.notification_tasks.send_sms")
def send_sms(phone: str, message: str) -> dict:
    """
    Send an SMS message via Twilio.

    This is a placeholder implementation. In production, integrate with
    the Twilio SDK:

        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone,
        )
    """
    # Validate phone number format
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if len(cleaned) < 10:
        logger.warning("Invalid phone number for SMS: %s", phone)
        return {"status": "failed", "reason": "invalid_phone", "phone": phone}

    # Truncate message to SMS limit
    sms_message = message[:1600]

    logger.info(
        "SMS placeholder: would send to %s (%d chars)",
        cleaned,
        len(sms_message),
    )

    # In production:
    # try:
    #     from twilio.rest import Client
    #     from app.core.config import settings
    #     client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    #     result = client.messages.create(
    #         body=sms_message,
    #         from_=settings.TWILIO_PHONE_NUMBER,
    #         to=cleaned,
    #     )
    #     return {"status": "sent", "sid": result.sid, "phone": cleaned}
    # except Exception as exc:
    #     logger.error("Twilio SMS failed: %s", exc)
    #     return {"status": "failed", "reason": str(exc), "phone": cleaned}

    return {"status": "sent_placeholder", "phone": cleaned, "message_length": len(sms_message)}


@celery_app.task(name="app.tasks.notification_tasks.send_email")
def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email via SendGrid.

    This is a placeholder implementation. In production, integrate with
    the SendGrid SDK:

        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=settings.FROM_EMAIL,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )
        sg.send(message)
    """
    if not to or "@" not in to:
        logger.warning("Invalid email address: %s", to)
        return {"status": "failed", "reason": "invalid_email", "to": to}

    logger.info(
        "Email placeholder: would send to %s, subject='%s' (%d chars body)",
        to,
        subject,
        len(body),
    )

    # In production:
    # try:
    #     import sendgrid
    #     from sendgrid.helpers.mail import Mail
    #     from app.core.config import settings
    #     sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    #     message = Mail(
    #         from_email=settings.FROM_EMAIL,
    #         to_emails=to,
    #         subject=subject,
    #         plain_text_content=body,
    #     )
    #     response = sg.send(message)
    #     return {
    #         "status": "sent",
    #         "to": to,
    #         "status_code": response.status_code,
    #     }
    # except Exception as exc:
    #     logger.error("SendGrid email failed: %s", exc)
    #     return {"status": "failed", "reason": str(exc), "to": to}

    return {"status": "sent_placeholder", "to": to, "subject": subject}


@celery_app.task(name="app.tasks.notification_tasks.create_notification")
def create_notification(
    recipient_type: str,
    recipient_id: str,
    title: str,
    body: str,
    category: str,
) -> dict:
    """
    Create an in-app notification record.

    Args:
        recipient_type: "landlord" or "tenant"
        recipient_id: UUID of the recipient
        title: Notification title
        body: Notification message body
        category: One of the NotificationType values (e.g., "payment_received")
    """
    return _run_async(
        _create_notification(recipient_type, uuid.UUID(recipient_id), title, body, category)
    )


async def _create_notification(
    recipient_type: str,
    recipient_id: uuid.UUID,
    title: str,
    body: str,
    category: str,
) -> dict:
    async with async_session_factory() as db:
        notification_type = CATEGORY_TYPE_MAP.get(category, NotificationType.SYSTEM)

        if recipient_type == "landlord":
            landlord_id = recipient_id
        elif recipient_type == "tenant":
            # Look up the tenant's landlord
            from app.models.tenant import Tenant
            result = await db.execute(
                select(Tenant).where(Tenant.id == recipient_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                logger.error("Tenant %s not found for notification", recipient_id)
                return {"status": "failed", "reason": "tenant_not_found"}
            landlord_id = tenant.landlord_id
        else:
            logger.error("Unknown recipient_type: %s", recipient_type)
            return {"status": "failed", "reason": "unknown_recipient_type"}

        notification = Notification(
            landlord_id=landlord_id,
            type=notification_type,
            title=title,
            message=body,
            data={
                "recipient_type": recipient_type,
                "recipient_id": str(recipient_id),
            },
        )
        db.add(notification)
        await db.commit()

        logger.info(
            "Notification created: '%s' for %s %s",
            title,
            recipient_type,
            recipient_id,
        )

        return {
            "status": "created",
            "notification_id": str(notification.id),
            "recipient_type": recipient_type,
            "recipient_id": str(recipient_id),
        }
