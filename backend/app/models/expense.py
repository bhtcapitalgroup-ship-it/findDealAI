"""Expense ORM model."""

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.user import User


class ExpenseCategory(str, enum.Enum):
    MAINTENANCE = "maintenance"
    INSURANCE = "insurance"
    TAXES = "taxes"
    MORTGAGE = "mortgage"
    UTILITIES = "utilities"
    MANAGEMENT = "management"
    LEGAL = "legal"
    MARKETING = "marketing"
    SUPPLIES = "supplies"
    OTHER = "other"


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    landlord_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    maintenance_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Relationships
    landlord: Mapped["User"] = relationship("User")
    property: Mapped[Optional["Property"]] = relationship("Property")

    def __repr__(self) -> str:
        return f"<Expense {self.category.value} {self.amount}>"
