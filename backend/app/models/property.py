"""Property ORM model for property management."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.unit import Unit
    from app.models.user import User


class PropertyType(str, enum.Enum):
    SFH = "sfh"
    MULTI = "multi"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"


class Property(TimestampMixin, Base):
    __tablename__ = "properties"

    landlord_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(500), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType, name="property_type"),
        default=PropertyType.SFH,
        nullable=False,
    )
    total_units: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    purchase_price: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    current_value: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    mortgage_payment: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    insurance_cost: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    tax_annual: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    # Relationships
    landlord: Mapped["User"] = relationship("User", back_populates="properties")
    units: Mapped[List["Unit"]] = relationship(
        "Unit", back_populates="property", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Property {self.name} ({self.address_line1})>"
