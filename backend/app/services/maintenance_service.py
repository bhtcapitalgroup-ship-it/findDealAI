"""Maintenance Service — Request lifecycle, contractor matching, and work completion."""

import logging
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.contractor import Contractor
from app.models.expense import Expense, ExpenseCategory
from app.models.maintenance import (
    MaintenanceCategory,
    MaintenancePhoto,
    MaintenanceRequest,
    MaintenanceStatus,
    MaintenanceUrgency,
)
from app.models.notification import Notification, NotificationType
from app.models.property import Property
from app.models.quote import Quote, QuoteStatus
from app.models.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MaintenanceService:
    """
    Manages the full lifecycle of maintenance requests: creation, AI diagnosis,
    contractor matching, quote approval, and completion.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Create request
    # ------------------------------------------------------------------

    async def create_request(
        self,
        unit_id: uuid.UUID,
        tenant_id: uuid.UUID,
        title: str,
        description: str,
        photos: list[dict] | None = None,
    ) -> MaintenanceRequest:
        """
        Create a new maintenance request with optional photos.

        Args:
            unit_id: The unit UUID
            tenant_id: The tenant UUID
            title: Short description of the issue
            description: Detailed description
            photos: List of dicts with 's3_key' and optional 'uploaded_by'
        """
        # Look up the property to get the landlord_id
        result = await self.db.execute(select(Unit).where(Unit.id == unit_id))
        unit = result.scalar_one()

        result = await self.db.execute(
            select(Property).where(Property.id == unit.property_id)
        )
        prop = result.scalar_one()

        request = MaintenanceRequest(
            unit_id=unit_id,
            tenant_id=tenant_id,
            landlord_id=prop.landlord_id,
            title=title,
            description=description,
            urgency=MaintenanceUrgency.ROUTINE,
            status=MaintenanceStatus.NEW,
        )
        self.db.add(request)
        await self.db.flush()

        # Attach photos
        if photos:
            image_keys: list[str] = []
            for photo_data in photos:
                photo = MaintenancePhoto(
                    request_id=request.id,
                    s3_key=photo_data["s3_key"],
                    uploaded_by=photo_data.get("uploaded_by", "tenant"),
                )
                self.db.add(photo)
                image_keys.append(photo_data["s3_key"])

            await self.db.flush()

            # Trigger AI vision diagnosis in background
            from app.tasks.maintenance_tasks import process_photo_diagnosis
            process_photo_diagnosis.delay(str(request.id), image_keys)

        # Notify landlord
        notification = Notification(
            landlord_id=prop.landlord_id,
            type=NotificationType.MAINTENANCE_NEW,
            title=f"New Maintenance Request: {title}",
            message=(
                f"Tenant reported an issue in unit {unit.unit_number}: {description}"
            ),
            data={
                "request_id": str(request.id),
                "unit_id": str(unit_id),
                "tenant_id": str(tenant_id),
            },
        )
        self.db.add(notification)
        await self.db.flush()

        logger.info(
            "Maintenance request %s created for unit %s: %s",
            request.id,
            unit.unit_number,
            title,
        )

        return request

    # ------------------------------------------------------------------
    # Contractor matching
    # ------------------------------------------------------------------

    async def match_contractors(
        self,
        request_id: uuid.UUID,
        limit: int = 5,
    ) -> list[Contractor]:
        """
        Find the best contractors for a maintenance request based on:
        - Trade match (primary filter)
        - Average rating (higher is better)
        - Availability (active status)
        - Total completed jobs (experience)

        Returns up to `limit` contractors sorted by rating.
        """
        result = await self.db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        # Determine the trade needed
        trade_needed = None
        if request.ai_diagnosis and "trade_needed" in request.ai_diagnosis:
            trade_needed = request.ai_diagnosis["trade_needed"]
        elif request.category:
            # Map maintenance category to trade
            category_to_trade = {
                MaintenanceCategory.PLUMBING: "plumber",
                MaintenanceCategory.ELECTRICAL: "electrician",
                MaintenanceCategory.HVAC: "hvac_tech",
                MaintenanceCategory.APPLIANCE: "appliance_repair",
                MaintenanceCategory.PEST: "pest_control",
                MaintenanceCategory.STRUCTURAL: "general_contractor",
                MaintenanceCategory.GENERAL: "general_contractor",
                MaintenanceCategory.LANDSCAPING: "general_contractor",
                MaintenanceCategory.OTHER: "general_contractor",
            }
            trade_needed = category_to_trade.get(
                request.category, "general_contractor"
            )

        # Query contractors belonging to this landlord
        query = (
            select(Contractor)
            .where(
                Contractor.landlord_id == request.landlord_id,
                Contractor.is_active.is_(True),
            )
            .order_by(
                Contractor.avg_rating.desc().nullslast(),
                Contractor.total_jobs.desc(),
            )
            .limit(limit)
        )

        # If we know the trade, filter by it
        if trade_needed:
            query = query.where(
                Contractor.trades.any(trade_needed)
            )

        result = await self.db.execute(query)
        contractors = result.scalars().all()

        # If trade-specific search yields too few, fall back to all active
        if len(contractors) < 2 and trade_needed:
            result = await self.db.execute(
                select(Contractor)
                .where(
                    Contractor.landlord_id == request.landlord_id,
                    Contractor.is_active.is_(True),
                )
                .order_by(
                    Contractor.avg_rating.desc().nullslast(),
                    Contractor.total_jobs.desc(),
                )
                .limit(limit)
            )
            contractors = result.scalars().all()

        logger.info(
            "Matched %d contractors for request %s (trade: %s)",
            len(contractors),
            request_id,
            trade_needed,
        )

        return list(contractors)

    # ------------------------------------------------------------------
    # Quote approval
    # ------------------------------------------------------------------

    async def approve_quote(
        self,
        request_id: uuid.UUID,
        quote_id: uuid.UUID,
    ) -> Quote:
        """
        Approve a contractor quote and schedule the work.

        - Marks the selected quote as ACCEPTED
        - Rejects all other quotes for this request
        - Updates the maintenance request status to APPROVED/SCHEDULED
        - Sets the scheduled date from the quote's available_date
        """
        # Accept the selected quote
        result = await self.db.execute(
            select(Quote).where(Quote.id == quote_id, Quote.request_id == request_id)
        )
        quote = result.scalar_one()
        quote.status = QuoteStatus.ACCEPTED

        # Reject all other pending quotes for this request
        result = await self.db.execute(
            select(Quote).where(
                Quote.request_id == request_id,
                Quote.id != quote_id,
                Quote.status == QuoteStatus.PENDING,
            )
        )
        other_quotes = result.scalars().all()
        for other in other_quotes:
            other.status = QuoteStatus.REJECTED

        # Update maintenance request
        result = await self.db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        if quote.available_date:
            request.status = MaintenanceStatus.SCHEDULED
            request.scheduled_date = quote.available_date
        else:
            request.status = MaintenanceStatus.APPROVED

        request.estimated_cost_low = float(quote.amount)
        request.estimated_cost_high = float(quote.amount)

        await self.db.flush()

        # Notify contractor
        result = await self.db.execute(
            select(Contractor).where(Contractor.id == quote.contractor_id)
        )
        contractor = result.scalar_one()

        if contractor.email:
            from app.tasks.notification_tasks import send_email
            send_email.delay(
                contractor.email,
                f"Quote Approved: {request.title}",
                (
                    f"Your quote of ${float(quote.amount):,.2f} for "
                    f"'{request.title}' has been approved.\n\n"
                    f"{'Scheduled for: ' + quote.available_date.isoformat() if quote.available_date else 'Please confirm your availability.'}\n\n"
                    f"Reference #: {str(request_id)[:8]}"
                ),
            )

        # Notify landlord
        notification = Notification(
            landlord_id=request.landlord_id,
            type=NotificationType.MAINTENANCE_UPDATE,
            title=f"Quote Approved: {request.title}",
            message=(
                f"Quote from {contractor.company_name} for ${float(quote.amount):,.2f} "
                f"has been approved."
            ),
            data={
                "request_id": str(request_id),
                "quote_id": str(quote_id),
                "contractor_id": str(contractor.id),
                "amount": float(quote.amount),
            },
        )
        self.db.add(notification)
        await self.db.flush()

        logger.info(
            "Quote %s approved for request %s (contractor: %s, amount: $%.2f)",
            quote_id,
            request_id,
            contractor.company_name,
            float(quote.amount),
        )

        return quote

    # ------------------------------------------------------------------
    # Complete request
    # ------------------------------------------------------------------

    async def complete_request(
        self,
        request_id: uuid.UUID,
        actual_cost: float,
        notes: str | None = None,
    ) -> MaintenanceRequest:
        """
        Mark a maintenance request as completed and create an associated
        expense record.

        Args:
            request_id: The maintenance request UUID
            actual_cost: The actual cost of the repair
            notes: Optional notes about the completion
        """
        result = await self.db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        request.status = MaintenanceStatus.COMPLETED
        request.completed_date = date.today()
        request.actual_cost = actual_cost

        # Determine the property for the expense
        result = await self.db.execute(select(Unit).where(Unit.id == request.unit_id))
        unit = result.scalar_one()

        # Create an expense record
        expense = Expense(
            landlord_id=request.landlord_id,
            property_id=unit.property_id,
            maintenance_request_id=request_id,
            category=ExpenseCategory.MAINTENANCE,
            amount=actual_cost,
            description=notes or f"Maintenance: {request.title}",
            vendor=None,
            expense_date=date.today(),
        )

        # If we have a contractor from an accepted quote, set vendor
        result = await self.db.execute(
            select(Quote)
            .join(Contractor, Quote.contractor_id == Contractor.id)
            .where(
                Quote.request_id == request_id,
                Quote.status == QuoteStatus.ACCEPTED,
            )
        )
        accepted_quote = result.scalar_one_or_none()
        if accepted_quote:
            result = await self.db.execute(
                select(Contractor).where(Contractor.id == accepted_quote.contractor_id)
            )
            contractor = result.scalar_one()
            expense.vendor = contractor.company_name

            # Update contractor's total jobs
            contractor.total_jobs = (contractor.total_jobs or 0) + 1

        self.db.add(expense)
        await self.db.flush()

        # Notify landlord
        notification = Notification(
            landlord_id=request.landlord_id,
            type=NotificationType.MAINTENANCE_UPDATE,
            title=f"Maintenance Complete: {request.title}",
            message=(
                f"Maintenance request '{request.title}' has been completed. "
                f"Actual cost: ${actual_cost:,.2f}."
            ),
            data={
                "request_id": str(request_id),
                "actual_cost": actual_cost,
                "expense_id": str(expense.id),
            },
        )
        self.db.add(notification)
        await self.db.flush()

        logger.info(
            "Maintenance request %s completed. Actual cost: $%.2f",
            request_id,
            actual_cost,
        )

        return request
