"""Financial Insights — AI-driven financial analysis for landlords."""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense, ExpenseCategory
from app.models.lease import Lease, LeaseStatus
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.property import Property
from app.models.unit import Unit, UnitStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Insight:
    type: str       # "warning" | "alert" | "info" | "opportunity"
    title: str
    body: str
    action: str     # Suggested next step


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FinancialInsightsService:
    """
    Generates actionable financial insights for a landlord by querying
    payments, expenses, leases, and unit data.
    """

    def __init__(self, db: AsyncSession, landlord_id: uuid.UUID):
        self.db = db
        self.landlord_id = landlord_id

    async def generate_all_insights(self) -> list[Insight]:
        """Run all insight generators and return the combined list."""
        insights: list[Insight] = []

        collection_insights = await self._collection_rate_warnings()
        insights.extend(collection_insights)

        expense_insights = await self._expense_anomalies()
        insights.extend(expense_insights)

        lease_insights = await self._lease_expiration_alerts()
        insights.extend(lease_insights)

        vacancy_insights = await self._vacancy_cost_analysis()
        insights.extend(vacancy_insights)

        return insights

    # ------------------------------------------------------------------
    # Collection rate warnings
    # ------------------------------------------------------------------

    async def _collection_rate_warnings(self) -> list[Insight]:
        """Identify properties or tenants with poor collection rates."""
        insights: list[Insight] = []
        today = date.today()
        first_of_month = today.replace(day=1)
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)

        # Get all active leases for this landlord
        result = await self.db.execute(
            select(Lease)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == self.landlord_id,
                Lease.status == LeaseStatus.ACTIVE,
            )
        )
        active_leases = result.scalars().all()

        if not active_leases:
            return insights

        total_expected = 0.0
        total_collected = 0.0

        for lease in active_leases:
            total_expected += float(lease.rent_amount)

            # Sum completed payments for last month
            result = await self.db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(
                    Payment.lease_id == lease.id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.due_date >= last_month_start,
                    Payment.due_date < first_of_month,
                )
            )
            collected = float(result.scalar_one())
            total_collected += collected

        if total_expected > 0:
            collection_rate = total_collected / total_expected
            if collection_rate < 0.85:
                insights.append(Insight(
                    type="warning",
                    title="Low Collection Rate",
                    body=(
                        f"Last month's collection rate was {collection_rate:.0%}. "
                        f"Collected ${total_collected:,.2f} of ${total_expected:,.2f} expected. "
                        f"This is below the 85% threshold."
                    ),
                    action="Review overdue payments and consider sending reminders or initiating late fee processing.",
                ))
            elif collection_rate < 0.95:
                insights.append(Insight(
                    type="info",
                    title="Collection Rate Below Target",
                    body=(
                        f"Last month's collection rate was {collection_rate:.0%}. "
                        f"Target is 95% or higher."
                    ),
                    action="Follow up with tenants who have outstanding balances.",
                ))

        # Check for individual tenants with overdue payments
        result = await self.db.execute(
            select(
                Payment.tenant_id,
                func.count(Payment.id).label("overdue_count"),
                func.sum(Payment.amount).label("overdue_total"),
            )
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == self.landlord_id,
                Payment.status == PaymentStatus.PENDING,
                Payment.due_date < today,
            )
            .group_by(Payment.tenant_id)
        )
        overdue_tenants = result.all()

        for row in overdue_tenants:
            if row.overdue_count >= 2:
                insights.append(Insight(
                    type="alert",
                    title="Tenant With Multiple Overdue Payments",
                    body=(
                        f"Tenant has {row.overdue_count} overdue payments "
                        f"totaling ${float(row.overdue_total):,.2f}."
                    ),
                    action="Review tenant account and consider sending a formal notice.",
                ))

        return insights

    # ------------------------------------------------------------------
    # Expense anomalies
    # ------------------------------------------------------------------

    async def _expense_anomalies(self) -> list[Insight]:
        """Detect unusual expense patterns by comparing to historical averages."""
        insights: list[Insight] = []
        today = date.today()
        current_month_start = today.replace(day=1)
        three_months_ago = (current_month_start - timedelta(days=90)).replace(day=1)

        # Get monthly expense totals by category for last 3 months
        result = await self.db.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("total"),
            )
            .where(
                Expense.landlord_id == self.landlord_id,
                Expense.expense_date >= three_months_ago,
                Expense.expense_date < current_month_start,
            )
            .group_by(Expense.category)
        )
        historical = {row.category: float(row.total) / 3 for row in result.all()}

        # Get current month expenses by category
        result = await self.db.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("total"),
            )
            .where(
                Expense.landlord_id == self.landlord_id,
                Expense.expense_date >= current_month_start,
            )
            .group_by(Expense.category)
        )
        current = {row.category: float(row.total) for row in result.all()}

        for category, current_total in current.items():
            avg = historical.get(category, 0)
            if avg > 0 and current_total > avg * 1.5:
                pct_increase = ((current_total - avg) / avg) * 100
                insights.append(Insight(
                    type="warning",
                    title=f"High {category.value.title()} Expenses",
                    body=(
                        f"This month's {category.value} expenses are ${current_total:,.2f}, "
                        f"which is {pct_increase:.0f}% above your 3-month average of ${avg:,.2f}."
                    ),
                    action=f"Review recent {category.value} expenses to identify the cause of the increase.",
                ))

        # Check total expenses vs total income
        result = await self.db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.landlord_id == self.landlord_id,
                Expense.expense_date >= current_month_start,
            )
        )
        total_expenses = float(result.scalar_one())

        result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == self.landlord_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.paid_date >= current_month_start,
            )
        )
        total_income = float(result.scalar_one())

        if total_income > 0 and total_expenses > total_income * 0.7:
            ratio = total_expenses / total_income
            insights.append(Insight(
                type="warning",
                title="High Expense Ratio",
                body=(
                    f"Expenses (${total_expenses:,.2f}) are {ratio:.0%} of income "
                    f"(${total_income:,.2f}) this month. A healthy ratio is below 50%."
                ),
                action="Review expenses and look for cost reduction opportunities.",
            ))

        return insights

    # ------------------------------------------------------------------
    # Lease expiration alerts
    # ------------------------------------------------------------------

    async def _lease_expiration_alerts(self) -> list[Insight]:
        """Alert on leases expiring in 30, 60, or 90 days."""
        insights: list[Insight] = []
        today = date.today()

        thresholds = [
            (30, "alert", "Lease Expiring Within 30 Days"),
            (60, "warning", "Lease Expiring Within 60 Days"),
            (90, "info", "Lease Expiring Within 90 Days"),
        ]

        for days, insight_type, title in thresholds:
            cutoff = today + timedelta(days=days)
            previous_cutoff = today + timedelta(days=days - 30) if days > 30 else today

            result = await self.db.execute(
                select(func.count(Lease.id))
                .join(Unit, Lease.unit_id == Unit.id)
                .join(Property, Unit.property_id == Property.id)
                .where(
                    Property.landlord_id == self.landlord_id,
                    Lease.status == LeaseStatus.ACTIVE,
                    Lease.end_date.isnot(None),
                    Lease.end_date > previous_cutoff,
                    Lease.end_date <= cutoff,
                )
            )
            count = result.scalar_one()

            if count > 0:
                insights.append(Insight(
                    type=insight_type,
                    title=title,
                    body=f"{count} lease{'s' if count != 1 else ''} expiring within {days} days.",
                    action="Contact tenants about renewal or begin listing units for new tenants.",
                ))

        return insights

    # ------------------------------------------------------------------
    # Vacancy cost analysis
    # ------------------------------------------------------------------

    async def _vacancy_cost_analysis(self) -> list[Insight]:
        """Calculate the cost of current vacancies."""
        insights: list[Insight] = []

        # Find all vacant units for this landlord
        result = await self.db.execute(
            select(Unit, Property)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.landlord_id == self.landlord_id,
                Unit.status == UnitStatus.VACANT,
            )
        )
        vacant_units = result.all()

        if not vacant_units:
            return insights

        total_monthly_loss = 0.0
        for unit, prop in vacant_units:
            market_rent = float(unit.market_rent) if unit.market_rent else 0.0
            total_monthly_loss += market_rent

        if total_monthly_loss > 0:
            annual_loss = total_monthly_loss * 12
            insights.append(Insight(
                type="opportunity",
                title="Vacancy Revenue Loss",
                body=(
                    f"You have {len(vacant_units)} vacant unit{'s' if len(vacant_units) != 1 else ''} "
                    f"costing an estimated ${total_monthly_loss:,.2f}/month "
                    f"(${annual_loss:,.2f}/year) in lost rent."
                ),
                action="Prioritize filling vacant units by listing them or adjusting rent prices.",
            ))
        elif len(vacant_units) > 0:
            insights.append(Insight(
                type="info",
                title="Vacant Units",
                body=f"You have {len(vacant_units)} vacant unit{'s' if len(vacant_units) != 1 else ''} without market rent estimates.",
                action="Set market rent values for vacant units to track vacancy costs.",
            ))

        return insights
