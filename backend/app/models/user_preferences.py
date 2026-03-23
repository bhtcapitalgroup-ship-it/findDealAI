"""UserPreferences ORM model — stores investment onboarding preferences."""

import enum
import uuid
from typing import Any, List, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy import JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUID


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserPreferences(TimestampMixin, Base):
    """One-to-one with User — captures investment goals set during onboarding.

    Preferences drive recommended markets, auto-created alerts, and
    personalised deal scoring.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Investment strategy
    investment_types: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment='e.g. ["rental", "brrrr", "flip", "wholesale"]',
    )

    # Target markets as structured JSON list
    target_markets: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        server_default="[]",
        comment='e.g. [{"city": "Austin", "state": "TX"}, ...]',
    )

    # Budget range
    budget_min: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )
    budget_max: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    # Return criteria
    min_cap_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    min_cash_flow: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Property types
    property_types: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment='e.g. ["single_family", "multi_family"]',
    )

    # Experience
    experience_level: Mapped[Optional[ExperienceLevel]] = mapped_column(
        Enum(ExperienceLevel, name="experience_level"),
        nullable=True,
    )

    # Onboarding progress
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    onboarding_step: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="preferences")

    def __repr__(self) -> str:
        return f"<UserPreferences user={self.user_id} step={self.onboarding_step}>"
