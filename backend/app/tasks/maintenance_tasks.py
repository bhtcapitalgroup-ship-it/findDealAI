"""Maintenance-related Celery tasks: contractor outreach, follow-ups, and AI diagnosis."""

import asyncio
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.contractor import Contractor
from app.models.maintenance import (
    MaintenancePhoto,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.models.notification import Notification, NotificationType
from app.models.property import Property
from app.models.quote import Quote, QuoteStatus
from app.models.unit import Unit
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
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.maintenance_tasks.contact_contractors")
def contact_contractors(request_id: str, contractor_ids: list[str]) -> dict:
    """Send request-for-quote (RFQ) emails to selected contractors."""
    return _run_async(
        _contact_contractors(
            uuid.UUID(request_id),
            [uuid.UUID(cid) for cid in contractor_ids],
        )
    )


async def _contact_contractors(
    request_id: uuid.UUID,
    contractor_ids: list[uuid.UUID],
) -> dict:
    async with async_session_factory() as db:
        # Load maintenance request details
        result = await db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        result = await db.execute(select(Unit).where(Unit.id == request.unit_id))
        unit = result.scalar_one()

        result = await db.execute(
            select(Property).where(Property.id == unit.property_id)
        )
        prop = result.scalar_one()

        contacted = 0
        for contractor_id in contractor_ids:
            result = await db.execute(
                select(Contractor).where(Contractor.id == contractor_id)
            )
            contractor = result.scalar_one_or_none()
            if not contractor or not contractor.is_active:
                continue

            # Compose RFQ message
            rfq_message = (
                f"Maintenance Request - RFQ\n\n"
                f"Property: {prop.name}\n"
                f"Address: {prop.address_line1}, {prop.city}, {prop.state} {prop.zip_code}\n"
                f"Unit: {unit.unit_number}\n\n"
                f"Issue: {request.title}\n"
                f"Description: {request.description}\n"
                f"Category: {request.category.value if request.category else 'General'}\n"
                f"Urgency: {request.urgency.value}\n"
            )

            if request.ai_diagnosis:
                rfq_message += (
                    f"\nAI Diagnosis:\n"
                    f"- {request.ai_diagnosis.get('description', 'N/A')}\n"
                    f"- Recommended: {request.ai_diagnosis.get('recommended_action', 'N/A')}\n"
                    f"- Estimated Cost: ${request.estimated_cost_low or 0:,.0f} - "
                    f"${request.estimated_cost_high or 0:,.0f}\n"
                )

            rfq_message += (
                f"\nPlease reply with your quote and earliest availability.\n"
                f"Reference #: {str(request_id)[:8]}"
            )

            # Send via email
            if contractor.email:
                from app.tasks.notification_tasks import send_email
                send_email.delay(
                    contractor.email,
                    f"RFQ: {request.title} at {prop.name}",
                    rfq_message,
                )
                contacted += 1

            # Create a pending quote record
            quote = Quote(
                request_id=request_id,
                contractor_id=contractor_id,
                amount=0,  # Pending contractor response
                status=QuoteStatus.PENDING,
                description="Awaiting contractor quote",
            )
            db.add(quote)

        # Update request status to quoting
        if contacted > 0 and request.status in (
            MaintenanceStatus.NEW,
            MaintenanceStatus.DIAGNOSED,
        ):
            request.status = MaintenanceStatus.QUOTING

        await db.commit()

        logger.info(
            "Contacted %d contractors for request %s", contacted, request_id
        )
        return {"contacted": contacted, "request_id": str(request_id)}


@celery_app.task(name="app.tasks.maintenance_tasks.follow_up_quote")
def follow_up_quote(request_id: str) -> dict:
    """Follow up on pending quotes that have not received responses."""
    return _run_async(_follow_up_quote(uuid.UUID(request_id)))


async def _follow_up_quote(request_id: uuid.UUID) -> dict:
    async with async_session_factory() as db:
        result = await db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        # Find quotes that are still pending
        result = await db.execute(
            select(Quote)
            .join(Contractor, Quote.contractor_id == Contractor.id)
            .where(
                Quote.request_id == request_id,
                Quote.status == QuoteStatus.PENDING,
            )
        )
        pending_quotes = result.scalars().all()

        followed_up = 0
        for quote in pending_quotes:
            # Check if quote was created more than 48 hours ago
            if quote.created_at and (
                date.today() - quote.created_at.date()
            ).days < 2:
                continue

            result = await db.execute(
                select(Contractor).where(Contractor.id == quote.contractor_id)
            )
            contractor = result.scalar_one()

            if contractor.email:
                from app.tasks.notification_tasks import send_email
                send_email.delay(
                    contractor.email,
                    f"Follow-Up: Quote Request for {request.title}",
                    (
                        f"Hi {contractor.contact_name},\n\n"
                        f"We're following up on our request for a quote for "
                        f"the following maintenance issue:\n\n"
                        f"Issue: {request.title}\n"
                        f"Description: {request.description}\n"
                        f"Urgency: {request.urgency.value}\n\n"
                        f"Please provide your quote and availability at your "
                        f"earliest convenience.\n\n"
                        f"Reference #: {str(request_id)[:8]}\n\n"
                        f"Thank you."
                    ),
                )
                followed_up += 1

        # Notify landlord about pending quotes
        if followed_up > 0:
            notification = Notification(
                landlord_id=request.landlord_id,
                type=NotificationType.MAINTENANCE_UPDATE,
                title="Quote Follow-Up Sent",
                message=(
                    f"Follow-up sent to {followed_up} contractor(s) for "
                    f"maintenance request: {request.title}."
                ),
                data={"request_id": str(request_id)},
            )
            db.add(notification)

        await db.commit()

        logger.info(
            "Followed up with %d contractors for request %s",
            followed_up,
            request_id,
        )
        return {"followed_up": followed_up, "request_id": str(request_id)}


@celery_app.task(
    name="app.tasks.maintenance_tasks.process_photo_diagnosis",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_photo_diagnosis(self, request_id: str, image_keys: list[str]) -> dict:
    """Run AI vision diagnostics on maintenance request photos."""
    try:
        return _run_async(
            _process_photo_diagnosis(uuid.UUID(request_id), image_keys)
        )
    except Exception as exc:
        logger.error(
            "Photo diagnosis failed for request %s: %s", request_id, exc
        )
        raise self.retry(exc=exc)


async def _process_photo_diagnosis(
    request_id: uuid.UUID,
    image_keys: list[str],
) -> dict:
    async with async_session_factory() as db:
        # Load the maintenance request
        result = await db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        # In production, fetch images from S3 using the keys.
        # For now, we simulate by loading photos from the database and
        # using placeholder image data.
        image_data_list: list[bytes] = []
        for key in image_keys:
            # Placeholder: in production, use boto3 to fetch from S3
            # s3_client.get_object(Bucket=bucket, Key=key)['Body'].read()
            # For now, we'll create minimal valid JPEG data for the API
            result = await db.execute(
                select(MaintenancePhoto).where(MaintenancePhoto.s3_key == key)
            )
            photo = result.scalar_one_or_none()
            if photo:
                # In production, download from S3 using photo.s3_key
                # For development, skip photos we can't download
                logger.info("Would fetch image from S3: %s", photo.s3_key)

        # If we have no actual image data, we can still run diagnosis
        # based on the text description alone
        if not image_data_list:
            logger.warning(
                "No images fetched for request %s; running text-only diagnosis",
                request_id,
            )

        from app.ai.vision_diagnostics import VisionDiagnosticsService

        vision_service = VisionDiagnosticsService(db)

        if image_data_list:
            diagnosis = await vision_service.diagnose_and_update(
                request_id=request_id,
                image_data=image_data_list,
                description=request.description,
            )
        else:
            # Text-only fallback: update request with basic info
            diagnosis = await vision_service.diagnose_and_update(
                request_id=request_id,
                image_data=[],
                description=request.description,
            )

        # Notify landlord about the diagnosis
        notification = Notification(
            landlord_id=request.landlord_id,
            type=NotificationType.MAINTENANCE_UPDATE,
            title=f"AI Diagnosis Complete: {request.title}",
            message=(
                f"Category: {diagnosis.category}\n"
                f"Severity: {diagnosis.severity}/5\n"
                f"Urgency: {diagnosis.urgency}\n"
                f"Trade needed: {diagnosis.trade_needed}\n"
                f"Est. cost: ${diagnosis.estimated_cost_low:,.0f} - "
                f"${diagnosis.estimated_cost_high:,.0f}\n\n"
                f"{diagnosis.description}"
            ),
            data={
                "request_id": str(request_id),
                "category": diagnosis.category,
                "severity": diagnosis.severity,
                "urgency": diagnosis.urgency,
            },
        )
        db.add(notification)

        # If emergency, send immediate notification
        if diagnosis.urgency == "emergency":
            from app.tasks.notification_tasks import create_notification
            create_notification.delay(
                "landlord",
                str(request.landlord_id),
                "EMERGENCY Maintenance Issue",
                (
                    f"An emergency maintenance issue has been detected: "
                    f"{diagnosis.description}. Immediate action required."
                ),
                "maintenance_update",
            )

        await db.commit()

        logger.info(
            "Photo diagnosis complete for request %s: %s (severity=%d)",
            request_id,
            diagnosis.category,
            diagnosis.severity,
        )

        return {
            "request_id": str(request_id),
            "category": diagnosis.category,
            "severity": diagnosis.severity,
            "urgency": diagnosis.urgency,
            "confidence": diagnosis.confidence,
            "estimated_cost_low": diagnosis.estimated_cost_low,
            "estimated_cost_high": diagnosis.estimated_cost_high,
        }
