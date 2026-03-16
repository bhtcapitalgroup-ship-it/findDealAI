"""Quote ORM model."""

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, Float, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.contractor import Contractor
    from app.models.maintenance import MaintenanceRequest


class QuoteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quote(TimestampMixin, Base):
    __tablename__ = "quotes"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    contractor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contractors.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(QuoteStatus, name="quote_status"),
        default=QuoteStatus.PENDING,
        server_default="pending",
        nullable=False,
        index=True,
    )

    # Relationships
    request: Mapped["MaintenanceRequest"] = relationship(
        "MaintenanceRequest", back_populates="quotes"
    )
    contractor: Mapped["Contractor"] = relationship("Contractor")

    def __repr__(self) -> str:
        return f"<Quote {self.amount} from contractor={self.contractor_id}>"
