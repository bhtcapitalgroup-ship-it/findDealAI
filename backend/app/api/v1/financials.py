"""Financial reporting API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.expense import Expense, ExpenseCategory
from app.models.lease import Lease, LeaseStatus
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus
from app.models.user import User
from app.schemas.financials import (
    CategoryExpense,
    DashboardSummary,
    ExpenseBreakdown,
    ExpenseCreate,
    ExpenseResponse,
    IncomeBreakdown,
    PropertyIncome,
)

router = APIRouter(prefix="/financials", tags=["financials"])


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    """Portfolio overview: units, occupancy, collections, NOI, cash flow."""
    # Total properties
    prop_count = (await db.execute(
        select(func.count()).select_from(Property).where(
            Property.landlord_id == current_user.id,
            Property.is_active == True,
        )
    )).scalar_one()

    # Total and occupied units
    total_units_result = await db.execute(
        select(func.count()).select_from(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.landlord_id == current_user.id, Property.is_active == True)
    )
    total_units = total_units_result.scalar_one()

    occupied_result = await db.execute(
        select(func.count()).select_from(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(
            Property.landlord_id == current_user.id,
            Property.is_active == True,
            Unit.status == UnitStatus.OCCUPIED,
        )
    )
    occupied_units = occupied_result.scalar_one()

    occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0.0

    # Total collected
    collected_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(
            Tenant.landlord_id == current_user.id,
            Payment.status == PaymentStatus.COMPLETED,
        )
    )
    total_collected = float(collected_result.scalar_one())

    # Total outstanding
    outstanding_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(
            Tenant.landlord_id == current_user.id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    total_outstanding = float(outstanding_result.scalar_one())

    # Total expenses
    expense_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.landlord_id == current_user.id,
        )
    )
    total_expenses = float(expense_result.scalar_one())

    noi = total_collected - total_expenses
    # Cash flow = NOI (simplified; in production would subtract mortgage, etc.)
    cash_flow = noi

    return DashboardSummary(
        total_properties=prop_count,
        total_units=total_units,
        occupied_units=occupied_units,
        occupancy_rate=occupancy_rate,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        total_expenses=total_expenses,
        noi=noi,
        cash_flow=cash_flow,
    )


@router.get("/income", response_model=IncomeBreakdown)
async def get_income_breakdown(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncomeBreakdown:
    """Income breakdown by property."""
    # Get all properties for landlord
    props_result = await db.execute(
        select(Property).where(
            Property.landlord_id == current_user.id,
            Property.is_active == True,
        )
    )
    properties = props_result.scalars().all()

    by_property = []
    grand_total = 0.0

    for prop in properties:
        # Get units for this property
        units_result = await db.execute(
            select(Unit.id).where(Unit.property_id == prop.id)
        )
        unit_ids = [row[0] for row in units_result.all()]

        if not unit_ids:
            by_property.append(PropertyIncome(
                property_id=prop.id,
                property_name=prop.name,
                total_income=0.0,
                units=0,
            ))
            continue

        income_stmt = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.unit_id.in_(unit_ids),
                Payment.status == PaymentStatus.COMPLETED,
            )
        )
        if start_date:
            income_stmt = income_stmt.where(Payment.paid_date >= start_date)
        if end_date:
            income_stmt = income_stmt.where(Payment.paid_date <= end_date)

        prop_income = float((await db.execute(income_stmt)).scalar_one())
        grand_total += prop_income

        by_property.append(PropertyIncome(
            property_id=prop.id,
            property_name=prop.name,
            total_income=prop_income,
            units=len(unit_ids),
        ))

    return IncomeBreakdown(total=grand_total, by_property=by_property)


@router.get("/expenses", response_model=ExpenseBreakdown)
async def get_expense_breakdown(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseBreakdown:
    """Expense breakdown by category."""
    stmt = (
        select(
            Expense.category,
            func.sum(Expense.amount),
            func.count(Expense.id),
        )
        .where(Expense.landlord_id == current_user.id)
        .group_by(Expense.category)
    )
    if start_date:
        stmt = stmt.where(Expense.expense_date >= start_date)
    if end_date:
        stmt = stmt.where(Expense.expense_date <= end_date)

    result = await db.execute(stmt)
    rows = result.all()

    by_category = []
    grand_total = 0.0
    for category, total, count in rows:
        cat_value = category.value if hasattr(category, 'value') else str(category)
        total_f = float(total)
        grand_total += total_f
        by_category.append(CategoryExpense(
            category=cat_value,
            total=total_f,
            count=count,
        ))

    return ExpenseBreakdown(total=grand_total, by_category=by_category)


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_expense(
    payload: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    """Log a manual expense."""
    # Verify property ownership if property_id provided
    if payload.property_id:
        prop_result = await db.execute(
            select(Property).where(Property.id == payload.property_id)
        )
        prop = prop_result.scalar_one_or_none()
        if prop is None or prop.landlord_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to log expenses for this property",
            )

    expense = Expense(
        landlord_id=current_user.id,
        property_id=payload.property_id,
        category=payload.category,
        amount=payload.amount,
        description=payload.description,
        vendor=payload.vendor,
        expense_date=payload.expense_date,
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)
