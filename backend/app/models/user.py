"""User (Landlord) ORM model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.property import Property
    from app.models.saved_deal import SavedDeal
    from app.models.tenant import Tenant


class PlanTier(str, enum.Enum):
    STARTER = "starter"
    GROWTH = "growth"
    PRO = "pro"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_account_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    plan_tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plan_tier"),
        default=PlanTier.STARTER,
        server_default="starter",
        nullable=False,
    )
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    # Relationships
    properties: Mapped[List["Property"]] = relationship(
        "Property", back_populates="landlord", cascade="all, delete-orphan", lazy="selectin"
    )
    tenants: Mapped[List["Tenant"]] = relationship(
        "Tenant", back_populates="landlord", cascade="all, delete-orphan", lazy="selectin"
    )
    saved_deals: Mapped[List["SavedDeal"]] = relationship(
        "SavedDeal", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def subscription_tier(self) -> str:
        """Alias for plan_tier used by the UserResponse schema."""
        return self.plan_tier.value if self.plan_tier else "starter"

    @property
    def daily_deal_count(self) -> int:
        """Placeholder for daily deal usage counter (tracked externally)."""
        return 0

    def __repr__(self) -> str:
        return f"<User {self.email}>"
