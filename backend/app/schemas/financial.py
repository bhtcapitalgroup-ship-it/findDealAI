"""Pydantic schemas for financial reporting."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class IncomeBreakdown(BaseModel):
    property_id: UUID
    property_name: str
    rent_collected: float
    other_income: float
    total: float


class IncomeReport(BaseModel):
    period_start: date
    period_end: date
    total_rent_collected: float
    total_other_income: float
    total_income: float
    by_property: List[IncomeBreakdown]


class ExpenseBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float


class ExpenseReport(BaseModel):
    period_start: date
    period_end: date
    total_expenses: float
    by_category: List[ExpenseBreakdown]
    by_property: List[dict]


class NOIReport(BaseModel):
    period_start: date
    period_end: date
    total_income: float
    total_expenses: float
    net_operating_income: float
    by_property: List[dict]


class PropertySnapshot(BaseModel):
    property_id: UUID
    property_name: str
    total_units: int
    occupied_units: int
    vacancy_rate: float
    monthly_income: float
    monthly_expenses: float
    noi: float


class DashboardResponse(BaseModel):
    total_properties: int
    total_units: int
    occupied_units: int
    vacancy_rate: float
    total_monthly_income: float
    total_monthly_expenses: float
    net_operating_income: float
    overdue_payments: int
    open_maintenance_requests: int
    upcoming_lease_expirations: int
    properties: List[PropertySnapshot]
