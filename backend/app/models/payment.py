"""Payment ORM model."""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.tenant import Tenant


class PaymentType(str, enum.Enum):
    RENT = "rent"
    LATE_FEE = "late_fee"
    DEPOSIT = "deposit"
    OTHER = "other"


class PaymentMethod(str, enum.Enum):
    STRIPE = "stripe"
    ACH = "ach"
    ZELLE = "zelle"
    CASH = "cash"
    CHECK = "check"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="payment_type"),
        default=PaymentType.RENT,
        nullable=False,
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod, name="payment_method"),
        nullable=True,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        server_default="pending",
        nullable=False,
        index=True,
    )
    stripe_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lease: Mapped["Lease"] = relationship("Lease", back_populates="payments")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.amount} {self.status.value}>"
