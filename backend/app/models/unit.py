"""Unit ORM model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.property import Property


class UnitStatus(str, enum.Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    TURNOVER = "turnover"


class Unit(TimestampMixin, Base):
    __tablename__ = "units"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    unit_number: Mapped[str] = mapped_column(String(50), nullable=False)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sqft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_rent: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    status: Mapped[UnitStatus] = mapped_column(
        Enum(UnitStatus, name="unit_status"),
        default=UnitStatus.VACANT,
        server_default="vacant",
        nullable=False,
        index=True,
    )

    # Relationships
    property: Mapped["Property"] = relationship("Property", back_populates="units")
    leases: Mapped[List["Lease"]] = relationship(
        "Lease", back_populates="unit", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Unit {self.unit_number}>"
