"""Maintenance ORM models."""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.quote import Quote
    from app.models.tenant import Tenant
    from app.models.unit import Unit
    from app.models.user import User


class MaintenanceCategory(str, enum.Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    APPLIANCE = "appliance"
    STRUCTURAL = "structural"
    PEST = "pest"
    LANDSCAPING = "landscaping"
    GENERAL = "general"
    OTHER = "other"


class MaintenanceUrgency(str, enum.Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"


class MaintenanceStatus(str, enum.Enum):
    NEW = "new"
    DIAGNOSED = "diagnosed"
    QUOTING = "quoting"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceRequest(TimestampMixin, Base):
    __tablename__ = "maintenance_requests"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    landlord_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[MaintenanceCategory]] = mapped_column(
        Enum(MaintenanceCategory, name="maintenance_category"),
        nullable=True,
    )
    urgency: Mapped[MaintenanceUrgency] = mapped_column(
        Enum(MaintenanceUrgency, name="maintenance_urgency"),
        default=MaintenanceUrgency.ROUTINE,
        nullable=False,
        index=True,
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(MaintenanceStatus, name="maintenance_status"),
        default=MaintenanceStatus.NEW,
        server_default="new",
        nullable=False,
        index=True,
    )
    ai_diagnosis: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost_low: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    estimated_cost_high: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    actual_cost: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tenant_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tenant_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit")
    tenant: Mapped["Tenant"] = relationship("Tenant")
    landlord: Mapped["User"] = relationship("User")
    photos: Mapped[List["MaintenancePhoto"]] = relationship(
        "MaintenancePhoto", back_populates="request",
        cascade="all, delete-orphan", lazy="selectin",
    )
    quotes: Mapped[List["Quote"]] = relationship(
        "Quote", back_populates="request",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MaintenanceRequest {self.title}>"


class MaintenancePhoto(TimestampMixin, Base):
    __tablename__ = "maintenance_photos"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    ai_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    request: Mapped["MaintenanceRequest"] = relationship(
        "MaintenanceRequest", back_populates="photos"
    )

    def __repr__(self) -> str:
        return f"<MaintenancePhoto {self.s3_key}>"
