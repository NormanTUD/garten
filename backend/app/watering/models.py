from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WateringEvent(Base):
    __tablename__ = "watering_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bed_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    water_amount_liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    weather_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_rain_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    soil_moisture_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    bed: Mapped["Bed | None"] = relationship(lazy="selectin")  # noqa: F821


class FertilizingEvent(Base):
    __tablename__ = "fertilizing_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bed_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fertilizer_type: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    bed: Mapped["Bed | None"] = relationship(lazy="selectin")  # noqa: F821

