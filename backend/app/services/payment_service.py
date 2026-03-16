"""Payment Service — Stripe integration, ACH setup, payment recording, and reporting."""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.lease import Lease, LeaseStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus, PaymentType
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class AgingBucket:
    label: str
    count: int
    total: float


@dataclass
class AgingReport:
    current: AgingBucket
    days_1_30: AgingBucket
    days_31_60: AgingBucket
    days_61_90: AgingBucket
    days_over_90: AgingBucket
    grand_total: float


@dataclass
class CollectionSummary:
    month: str
    total_expected: float
    total_collected: float
    total_outstanding: float
    collection_rate: float
    payments_completed: int
    payments_pending: int


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PaymentService:
    """
    Handles payment processing, Stripe integration, ACH setup via Plaid,
    and financial reporting.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------

    async def create_stripe_payment_intent(
        self,
        amount: float,
        tenant_stripe_id: str,
        currency: str = "usd",
        description: str = "Rent payment",
    ) -> dict:
        """
        Create a Stripe PaymentIntent for a tenant.

        In production, uses the Stripe SDK:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            intent = stripe.PaymentIntent.create(...)

        Returns the client_secret for front-end confirmation.
        """
        amount_cents = int(amount * 100)

        logger.info(
            "Creating Stripe PaymentIntent: %d cents for customer %s",
            amount_cents,
            tenant_stripe_id,
        )

        # Production implementation:
        # import stripe
        # stripe.api_key = settings.STRIPE_SECRET_KEY
        # intent = stripe.PaymentIntent.create(
        #     amount=amount_cents,
        #     currency=currency,
        #     customer=tenant_stripe_id,
        #     description=description,
        #     automatic_payment_methods={"enabled": True},
        #     metadata={"platform": "realdeal"},
        # )
        # return {
        #     "payment_intent_id": intent.id,
        #     "client_secret": intent.client_secret,
        #     "status": intent.status,
        # }

        # Placeholder response
        placeholder_id = f"pi_{uuid.uuid4().hex[:24]}"
        return {
            "payment_intent_id": placeholder_id,
            "client_secret": f"{placeholder_id}_secret_{uuid.uuid4().hex[:12]}",
            "status": "requires_confirmation",
            "amount": amount_cents,
            "currency": currency,
        }

    # ------------------------------------------------------------------
    # Plaid / ACH
    # ------------------------------------------------------------------

    async def setup_ach_via_plaid(
        self,
        tenant_id: uuid.UUID,
        public_token: str,
    ) -> dict:
        """
        Exchange a Plaid public_token for an access_token, then retrieve
        the bank account details for ACH payments.

        In production:
            from plaid.api import plaid_api
            client = plaid_api.PlaidApi(...)
            exchange = client.item_public_token_exchange(public_token)
            access_token = exchange.access_token
            auth = client.auth_get(access_token)
            account = auth.accounts[0]
        """
        logger.info(
            "Setting up ACH via Plaid for tenant %s with public_token %s...",
            tenant_id,
            public_token[:8],
        )

        # Update tenant's stripe customer with bank info in production
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one()

        # Production: exchange token, attach bank account to Stripe customer
        # For now, return placeholder
        return {
            "status": "linked",
            "tenant_id": str(tenant_id),
            "bank_name": "Placeholder Bank",
            "account_last_four": "1234",
            "account_type": "checking",
        }

    # ------------------------------------------------------------------
    # Payment recording
    # ------------------------------------------------------------------

    async def record_payment(
        self,
        lease_id: uuid.UUID,
        amount: float,
        method: PaymentMethod,
        stripe_id: str | None = None,
        payment_type: PaymentType = PaymentType.RENT,
        notes: str | None = None,
    ) -> Payment:
        """
        Record a completed payment against a lease.

        Finds the oldest pending payment for the lease and marks it
        as completed, or creates a new payment record if no pending
        record exists.
        """
        result = await self.db.execute(
            select(Lease).where(Lease.id == lease_id)
        )
        lease = result.scalar_one()

        today = date.today()

        # Try to find and update an existing pending payment
        result = await self.db.execute(
            select(Payment)
            .where(
                Payment.lease_id == lease_id,
                Payment.status == PaymentStatus.PENDING,
                Payment.payment_type == payment_type,
            )
            .order_by(Payment.due_date.asc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing and abs(float(existing.amount) - amount) < 0.01:
            # Exact match — mark as completed
            existing.status = PaymentStatus.COMPLETED
            existing.payment_method = method
            existing.stripe_payment_id = stripe_id
            existing.paid_date = today
            if notes:
                existing.notes = notes
            payment = existing
        else:
            # Create new payment record
            payment = Payment(
                lease_id=lease_id,
                tenant_id=lease.tenant_id,
                amount=amount,
                payment_type=payment_type,
                payment_method=method,
                status=PaymentStatus.COMPLETED,
                stripe_payment_id=stripe_id,
                due_date=today,
                paid_date=today,
                notes=notes,
            )
            self.db.add(payment)

        await self.db.flush()

        # Trigger receipt generation
        from app.tasks.payment_tasks import generate_receipt
        generate_receipt.delay(str(payment.id))

        logger.info(
            "Payment of $%.2f recorded for lease %s via %s",
            amount,
            lease_id,
            method.value,
        )

        return payment

    # ------------------------------------------------------------------
    # Aging report
    # ------------------------------------------------------------------

    async def get_aging_report(self, landlord_id: uuid.UUID) -> AgingReport:
        """
        Group outstanding payments by age buckets:
        - Current (not yet due)
        - 1-30 days overdue
        - 31-60 days overdue
        - 61-90 days overdue
        - 90+ days overdue
        """
        today = date.today()

        result = await self.db.execute(
            select(Payment)
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == landlord_id,
                Payment.status == PaymentStatus.PENDING,
            )
        )
        pending_payments = result.scalars().all()

        buckets = {
            "current": {"count": 0, "total": 0.0},
            "1-30": {"count": 0, "total": 0.0},
            "31-60": {"count": 0, "total": 0.0},
            "61-90": {"count": 0, "total": 0.0},
            "90+": {"count": 0, "total": 0.0},
        }

        for payment in pending_payments:
            days_overdue = (today - payment.due_date).days
            amount = float(payment.amount)

            if days_overdue <= 0:
                buckets["current"]["count"] += 1
                buckets["current"]["total"] += amount
            elif days_overdue <= 30:
                buckets["1-30"]["count"] += 1
                buckets["1-30"]["total"] += amount
            elif days_overdue <= 60:
                buckets["31-60"]["count"] += 1
                buckets["31-60"]["total"] += amount
            elif days_overdue <= 90:
                buckets["61-90"]["count"] += 1
                buckets["61-90"]["total"] += amount
            else:
                buckets["90+"]["count"] += 1
                buckets["90+"]["total"] += amount

        grand_total = sum(b["total"] for b in buckets.values())

        return AgingReport(
            current=AgingBucket("Current", buckets["current"]["count"], buckets["current"]["total"]),
            days_1_30=AgingBucket("1-30 Days", buckets["1-30"]["count"], buckets["1-30"]["total"]),
            days_31_60=AgingBucket("31-60 Days", buckets["31-60"]["count"], buckets["31-60"]["total"]),
            days_61_90=AgingBucket("61-90 Days", buckets["61-90"]["count"], buckets["61-90"]["total"]),
            days_over_90=AgingBucket("90+ Days", buckets["90+"]["count"], buckets["90+"]["total"]),
            grand_total=grand_total,
        )

    # ------------------------------------------------------------------
    # Collection summary
    # ------------------------------------------------------------------

    async def get_collection_summary(
        self,
        landlord_id: uuid.UUID,
        month: date,
    ) -> CollectionSummary:
        """
        Get totals collected vs outstanding for a given month.

        Args:
            landlord_id: The landlord UUID
            month: Any date in the target month (day is ignored)
        """
        month_start = month.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        # Expected rent from active leases
        result = await self.db.execute(
            select(func.coalesce(func.sum(Lease.rent_amount), 0))
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == landlord_id,
                Lease.status == LeaseStatus.ACTIVE,
                Lease.start_date <= month_end,
            )
        )
        total_expected = float(result.scalar_one())

        # Collected payments
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Payment.amount), 0),
                func.count(Payment.id),
            )
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == landlord_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.due_date >= month_start,
                Payment.due_date < month_end,
            )
        )
        row = result.one()
        total_collected = float(row[0])
        payments_completed = row[1]

        # Pending payments
        result = await self.db.execute(
            select(func.count(Payment.id))
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == landlord_id,
                Payment.status == PaymentStatus.PENDING,
                Payment.due_date >= month_start,
                Payment.due_date < month_end,
            )
        )
        payments_pending = result.scalar_one()

        total_outstanding = max(0, total_expected - total_collected)
        collection_rate = (
            total_collected / total_expected if total_expected > 0 else 0.0
        )

        return CollectionSummary(
            month=month_start.strftime("%Y-%m"),
            total_expected=total_expected,
            total_collected=total_collected,
            total_outstanding=total_outstanding,
            collection_rate=round(collection_rate, 4),
            payments_completed=payments_completed,
            payments_pending=payments_pending,
        )
