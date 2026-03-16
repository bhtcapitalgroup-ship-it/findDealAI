"""SavedDeal ORM model — links users to properties they have saved."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.user import User


class SavedDeal(TimestampMixin, Base):
    __tablename__ = "saved_deals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_arv: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    custom_rehab: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    custom_rent: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="saved_deals")
    property: Mapped["Property"] = relationship("Property", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SavedDeal user={self.user_id} property={self.property_id}>"
