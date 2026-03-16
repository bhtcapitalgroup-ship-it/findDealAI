"""MarketData ORM model — zipcode-level market snapshots."""

from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MarketData(TimestampMixin, Base):
    __tablename__ = "market_data"

    zip_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    metro_area: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    median_price: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    median_rent: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    price_growth_yoy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rent_growth_yoy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inventory_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    days_on_market_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    population_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unemployment_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_income: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    crime_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    school_rating_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    migration_inflow: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    migration_outflow: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    snapshot_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<MarketData {self.zip_code} {self.snapshot_date}>"
