"""Payment-related Celery tasks: rent reminders, late fees, receipts, and periodic checks."""

import asyncio
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.lease import Lease, LeaseStatus
from app.models.notification import Notification, NotificationType
from app.models.payment import Payment, PaymentMethod, PaymentStatus, PaymentType
from app.models.property import Property
from app.models.tenant import Tenant
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
# Individual tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.payment_tasks.send_rent_reminder")
def send_rent_reminder(tenant_id: str, lease_id: str) -> dict:
    """Compose and send a rent reminder to a tenant."""
    return _run_async(_send_rent_reminder(uuid.UUID(tenant_id), uuid.UUID(lease_id)))


async def _send_rent_reminder(tenant_id: uuid.UUID, lease_id: uuid.UUID) -> dict:
    async with async_session_factory() as db:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        result = await db.execute(select(Lease).where(Lease.id == lease_id))
        lease = result.scalar_one()

        result = await db.execute(select(Unit).where(Unit.id == lease.unit_id))
        unit = result.scalar_one()

        message = (
            f"Hi {tenant.first_name}, this is a friendly reminder that your "
            f"rent of ${float(lease.rent_amount):,.2f} for unit {unit.unit_number} "
            f"is due on day {lease.rent_due_day} of this month. "
            f"Please submit your payment at your earliest convenience."
        )

        # Send via available channels
        if tenant.phone:
            from app.tasks.notification_tasks import send_sms
            send_sms.delay(tenant.phone, message)

        if tenant.email:
            from app.tasks.notification_tasks import send_email
            send_email.delay(
                tenant.email,
                "Rent Payment Reminder",
                message,
            )

        # Create in-app notification for the landlord
        from app.tasks.notification_tasks import create_notification
        create_notification.delay(
            "landlord",
            str(tenant.landlord_id),
            "Rent Reminder Sent",
            f"Rent reminder sent to {tenant.first_name} {tenant.last_name} for unit {unit.unit_number}.",
            "payment_received",
        )

        await db.commit()

        logger.info("Rent reminder sent to tenant %s for lease %s", tenant_id, lease_id)
        return {"status": "sent", "tenant_id": str(tenant_id), "lease_id": str(lease_id)}


@celery_app.task(name="app.tasks.payment_tasks.process_late_fee")
def process_late_fee(lease_id: str) -> dict:
    """Calculate and create a late fee payment record."""
    return _run_async(_process_late_fee(uuid.UUID(lease_id)))


async def _process_late_fee(lease_id: uuid.UUID) -> dict:
    async with async_session_factory() as db:
        result = await db.execute(select(Lease).where(Lease.id == lease_id))
        lease = result.scalar_one()

        if not lease.late_fee_amount or float(lease.late_fee_amount) <= 0:
            return {"status": "skipped", "reason": "no_late_fee_configured"}

        today = date.today()

        # Check if a late fee has already been created for this period
        result = await db.execute(
            select(Payment).where(
                Payment.lease_id == lease_id,
                Payment.payment_type == PaymentType.LATE_FEE,
                Payment.due_date >= today.replace(day=1),
            )
        )
        existing_fee = result.scalar_one_or_none()
        if existing_fee:
            return {"status": "skipped", "reason": "late_fee_already_exists"}

        # Create the late fee payment record
        late_fee = Payment(
            lease_id=lease_id,
            tenant_id=lease.tenant_id,
            amount=float(lease.late_fee_amount),
            payment_type=PaymentType.LATE_FEE,
            status=PaymentStatus.PENDING,
            due_date=today,
            notes=f"Late fee assessed on {today.isoformat()}",
        )
        db.add(late_fee)

        # Notify the tenant
        result = await db.execute(select(Tenant).where(Tenant.id == lease.tenant_id))
        tenant = result.scalar_one()

        notification = Notification(
            landlord_id=tenant.landlord_id,
            type=NotificationType.PAYMENT_OVERDUE,
            title="Late Fee Assessed",
            message=(
                f"A late fee of ${float(lease.late_fee_amount):,.2f} has been "
                f"assessed to {tenant.first_name} {tenant.last_name}."
            ),
            data={"lease_id": str(lease_id), "amount": float(lease.late_fee_amount)},
        )
        db.add(notification)

        await db.commit()

        logger.info("Late fee of $%.2f created for lease %s", float(lease.late_fee_amount), lease_id)
        return {
            "status": "created",
            "lease_id": str(lease_id),
            "amount": float(lease.late_fee_amount),
        }


@celery_app.task(name="app.tasks.payment_tasks.generate_receipt")
def generate_receipt(payment_id: str) -> dict:
    """Generate a payment receipt for a completed payment."""
    return _run_async(_generate_receipt(uuid.UUID(payment_id)))


async def _generate_receipt(payment_id: uuid.UUID) -> dict:
    async with async_session_factory() as db:
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one()

        result = await db.execute(select(Tenant).where(Tenant.id == payment.tenant_id))
        tenant = result.scalar_one()

        result = await db.execute(select(Lease).where(Lease.id == payment.lease_id))
        lease = result.scalar_one()

        result = await db.execute(select(Unit).where(Unit.id == lease.unit_id))
        unit = result.scalar_one()

        result = await db.execute(select(Property).where(Property.id == unit.property_id))
        prop = result.scalar_one()

        receipt = {
            "receipt_id": str(payment.id),
            "date": payment.paid_date.isoformat() if payment.paid_date else date.today().isoformat(),
            "tenant_name": f"{tenant.first_name} {tenant.last_name}",
            "property_name": prop.name,
            "property_address": f"{prop.address_line1}, {prop.city}, {prop.state} {prop.zip_code}",
            "unit_number": unit.unit_number,
            "amount": float(payment.amount),
            "payment_type": payment.payment_type.value,
            "payment_method": payment.payment_method.value if payment.payment_method else "N/A",
            "stripe_id": payment.stripe_payment_id or "N/A",
            "status": payment.status.value,
        }

        # Send receipt via email
        if tenant.email:
            from app.tasks.notification_tasks import send_email
            receipt_body = (
                f"Payment Receipt\n\n"
                f"Property: {prop.name}\n"
                f"Unit: {unit.unit_number}\n"
                f"Amount: ${float(payment.amount):,.2f}\n"
                f"Type: {payment.payment_type.value}\n"
                f"Date: {receipt['date']}\n"
                f"Receipt ID: {receipt['receipt_id']}\n\n"
                f"Thank you for your payment!"
            )
            send_email.delay(tenant.email, "Payment Receipt", receipt_body)

        logger.info("Receipt generated for payment %s", payment_id)
        return receipt


# ---------------------------------------------------------------------------
# Periodic / beat tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.payment_tasks.check_rent_due")
def check_rent_due() -> dict:
    """Find leases with rent due today and send reminders."""
    return _run_async(_check_rent_due())


async def _check_rent_due() -> dict:
    today = date.today()
    reminders_sent = 0

    async with async_session_factory() as db:
        # Find active leases where rent_due_day matches today
        result = await db.execute(
            select(Lease).where(
                Lease.status == LeaseStatus.ACTIVE,
                Lease.rent_due_day == today.day,
            )
        )
        leases = result.scalars().all()

        for lease in leases:
            # Check if rent has already been paid this month
            result = await db.execute(
                select(Payment).where(
                    Payment.lease_id == lease.id,
                    Payment.payment_type == PaymentType.RENT,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.due_date >= today.replace(day=1),
                )
            )
            already_paid = result.scalar_one_or_none()
            if already_paid:
                continue

            send_rent_reminder.delay(str(lease.tenant_id), str(lease.id))
            reminders_sent += 1

    logger.info("check_rent_due: sent %d reminders", reminders_sent)
    return {"reminders_sent": reminders_sent}


@celery_app.task(name="app.tasks.payment_tasks.check_late_payments")
def check_late_payments() -> dict:
    """Find overdue payments and send escalating reminders / assess late fees."""
    return _run_async(_check_late_payments())


async def _check_late_payments() -> dict:
    today = date.today()
    actions_taken = 0

    async with async_session_factory() as db:
        # Find active leases
        result = await db.execute(
            select(Lease).where(Lease.status == LeaseStatus.ACTIVE)
        )
        leases = result.scalars().all()

        for lease in leases:
            grace_days = lease.late_fee_grace_days or 5
            due_day = lease.rent_due_day or 1

            # Calculate this month's due date
            try:
                due_date = today.replace(day=due_day)
            except ValueError:
                # If the day doesn't exist this month (e.g., day 31 in Feb),
                # use the last day of the month
                import calendar
                last_day = calendar.monthrange(today.year, today.month)[1]
                due_date = today.replace(day=min(due_day, last_day))

            # Only process if we're past the grace period
            if today <= due_date + timedelta(days=grace_days):
                continue

            # Check for unpaid rent this month
            result = await db.execute(
                select(Payment).where(
                    Payment.lease_id == lease.id,
                    Payment.payment_type == PaymentType.RENT,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.due_date >= today.replace(day=1),
                )
            )
            paid = result.scalar_one_or_none()
            if paid:
                continue

            days_overdue = (today - due_date).days

            # Escalating actions based on how overdue
            if days_overdue <= grace_days + 1:
                # Just past grace period — send gentle reminder
                send_rent_reminder.delay(str(lease.tenant_id), str(lease.id))
                actions_taken += 1

            elif days_overdue <= grace_days + 3:
                # Assess late fee
                process_late_fee.delay(str(lease.id))
                actions_taken += 1

            else:
                # Overdue beyond grace + 3 days — urgent notification
                result = await db.execute(
                    select(Tenant).where(Tenant.id == lease.tenant_id)
                )
                tenant = result.scalar_one()

                notification = Notification(
                    landlord_id=tenant.landlord_id,
                    type=NotificationType.PAYMENT_OVERDUE,
                    title="Severely Overdue Payment",
                    message=(
                        f"{tenant.first_name} {tenant.last_name}'s rent is "
                        f"{days_overdue} days overdue. Amount: ${float(lease.rent_amount):,.2f}."
                    ),
                    data={
                        "lease_id": str(lease.id),
                        "tenant_id": str(lease.tenant_id),
                        "days_overdue": days_overdue,
                    },
                )
                db.add(notification)
                actions_taken += 1

        await db.commit()

    logger.info("check_late_payments: %d actions taken", actions_taken)
    return {"actions_taken": actions_taken}


@celery_app.task(name="app.tasks.payment_tasks.check_lease_expirations")
def check_lease_expirations() -> dict:
    """Find leases expiring in 90/60/30 days and create notifications."""
    return _run_async(_check_lease_expirations())


async def _check_lease_expirations() -> dict:
    today = date.today()
    notifications_created = 0

    async with async_session_factory() as db:
        thresholds = [
            (30, "Lease Expiring in 30 Days"),
            (60, "Lease Expiring in 60 Days"),
            (90, "Lease Expiring in 90 Days"),
        ]

        for days, title in thresholds:
            target_date = today + timedelta(days=days)
            # Find leases ending within a 7-day window around the target
            window_start = target_date - timedelta(days=3)
            window_end = target_date + timedelta(days=3)

            result = await db.execute(
                select(Lease)
                .join(Unit, Lease.unit_id == Unit.id)
                .join(Property, Unit.property_id == Property.id)
                .where(
                    Lease.status == LeaseStatus.ACTIVE,
                    Lease.end_date.isnot(None),
                    Lease.end_date >= window_start,
                    Lease.end_date <= window_end,
                )
            )
            leases = result.scalars().all()

            for lease in leases:
                result = await db.execute(select(Tenant).where(Tenant.id == lease.tenant_id))
                tenant = result.scalar_one()

                result = await db.execute(select(Unit).where(Unit.id == lease.unit_id))
                unit = result.scalar_one()

                result = await db.execute(
                    select(Property).where(Property.id == unit.property_id)
                )
                prop = result.scalar_one()

                notification = Notification(
                    landlord_id=prop.landlord_id,
                    type=NotificationType.LEASE_EXPIRING,
                    title=title,
                    message=(
                        f"Lease for {tenant.first_name} {tenant.last_name} "
                        f"in unit {unit.unit_number} at {prop.name} "
                        f"expires on {lease.end_date.isoformat()}."
                    ),
                    data={
                        "lease_id": str(lease.id),
                        "tenant_id": str(lease.tenant_id),
                        "unit_id": str(unit.id),
                        "end_date": lease.end_date.isoformat(),
                    },
                )
                db.add(notification)
                notifications_created += 1

                # Send email to tenant about upcoming expiration
                if tenant.email:
                    from app.tasks.notification_tasks import send_email
                    send_email.delay(
                        tenant.email,
                        f"Lease Renewal Notice - {prop.name}",
                        (
                            f"Hi {tenant.first_name},\n\n"
                            f"Your lease for unit {unit.unit_number} at {prop.name} "
                            f"is set to expire on {lease.end_date.isoformat()}.\n\n"
                            f"Please contact your property manager to discuss "
                            f"renewal options.\n\nThank you."
                        ),
                    )

        await db.commit()

    logger.info("check_lease_expirations: %d notifications created", notifications_created)
    return {"notifications_created": notifications_created}


@celery_app.task(name="app.tasks.payment_tasks.generate_monthly_report")
def generate_monthly_report() -> dict:
    """Generate monthly financial report for all landlords."""
    return _run_async(_generate_monthly_report())


async def _generate_monthly_report() -> dict:
    from app.ai.financial_insights import FinancialInsightsService
    from app.models.user import User

    reports_generated = 0

    async with async_session_factory() as db:
        # Get all active landlords (users who own properties)
        result = await db.execute(
            select(User.id).join(Property, Property.landlord_id == User.id).distinct()
        )
        landlord_ids = [row[0] for row in result.all()]

        for landlord_id in landlord_ids:
            service = FinancialInsightsService(db, landlord_id)
            insights = await service.generate_all_insights()

            if insights:
                # Create a summary notification
                summary_lines = [f"- {i.title}: {i.body}" for i in insights[:5]]
                summary = "\n".join(summary_lines)

                notification = Notification(
                    landlord_id=landlord_id,
                    type=NotificationType.SYSTEM,
                    title="Monthly Financial Report",
                    message=f"Your monthly financial insights:\n\n{summary}",
                    data={
                        "insights_count": len(insights),
                        "insights": [
                            {"type": i.type, "title": i.title, "body": i.body, "action": i.action}
                            for i in insights
                        ],
                    },
                )
                db.add(notification)
                reports_generated += 1

        await db.commit()

    logger.info("generate_monthly_report: %d reports generated", reports_generated)
    return {"reports_generated": reports_generated}
