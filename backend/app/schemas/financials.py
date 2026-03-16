"""Pydantic schemas for financial reporting."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    """Portfolio financial overview."""

    total_properties: int
    total_units: int
    occupied_units: int
    occupancy_rate: float
    total_collected: float
    total_outstanding: float
    total_expenses: float
    noi: float
    cash_flow: float


class PropertyIncome(BaseModel):
    """Income breakdown for a single property."""

    property_id: UUID
    property_name: str
    total_income: float
    units: int


class IncomeBreakdown(BaseModel):
    """Income breakdown across portfolio."""

    total: float
    by_property: List[PropertyIncome]


class CategoryExpense(BaseModel):
    """Expense for a single category."""

    category: str
    total: float
    count: int


class ExpenseBreakdown(BaseModel):
    """Expense breakdown by category."""

    total: float
    by_category: List[CategoryExpense]


class ExpenseCreate(BaseModel):
    """Schema for logging a manual expense."""

    property_id: Optional[UUID] = None
    category: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    vendor: Optional[str] = None
    expense_date: date


class ExpenseResponse(BaseModel):
    """Expense detail response."""

    id: UUID
    landlord_id: UUID
    property_id: Optional[UUID] = None
    category: str
    amount: float
    description: Optional[str] = None
    vendor: Optional[str] = None
    expense_date: date
    created_at: datetime

    model_config = {"from_attributes": True}
