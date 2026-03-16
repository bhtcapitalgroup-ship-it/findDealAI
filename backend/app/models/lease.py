"""Lease ORM model."""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.tenant import Tenant
    from app.models.unit import Unit


class LeaseType(str, enum.Enum):
    FIXED = "fixed"
    MONTH_TO_MONTH = "month_to_month"


class LeaseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class Lease(TimestampMixin, Base):
    __tablename__ = "leases"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rent_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    rent_due_day: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    late_fee_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    late_fee_grace_days: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5", nullable=False
    )
    lease_type: Mapped[LeaseType] = mapped_column(
        Enum(LeaseType, name="lease_type"),
        default=LeaseType.FIXED,
        nullable=False,
    )
    status: Mapped[LeaseStatus] = mapped_column(
        Enum(LeaseStatus, name="lease_status"),
        default=LeaseStatus.ACTIVE,
        server_default="active",
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    ai_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="leases")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="leases")
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="lease", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Lease unit={self.unit_id} tenant={self.tenant_id}>"
