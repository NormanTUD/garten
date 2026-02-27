from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Harvest(Base):
    __tablename__ = "harvests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bed_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    plant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    plant: Mapped["Plant | None"] = relationship(lazy="selectin")  # noqa: F821

