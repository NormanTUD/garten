from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    variety: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_water_needs: Mapped[str | None] = mapped_column(String(20), nullable=True)
    growing_season_start: Mapped[int | None] = mapped_column(Integer, nullable=True)  # month 1-12
    growing_season_end: Mapped[int | None] = mapped_column(Integer, nullable=True)  # month 1-12
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    plantings: Mapped[list["BedPlanting"]] = relationship(  # noqa: F821
        back_populates="plant",
        cascade="all, delete-orphan",
    )

