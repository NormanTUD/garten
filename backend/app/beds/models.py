import json
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Bed(Base):
    __tablename__ = "beds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    garden_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gardens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sun_exposure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    garden: Mapped["Garden"] = relationship(back_populates="beds")  # noqa: F821
    plantings: Mapped[list["BedPlanting"]] = relationship(
        back_populates="bed",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def geometry_dict(self) -> dict | None:
        if self.geometry is None:
            return None
        return json.loads(self.geometry)


class BedPlanting(Base):
    __tablename__ = "bed_plantings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bed_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("beds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    planted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    bed: Mapped["Bed"] = relationship(back_populates="plantings")
    plant: Mapped["Plant"] = relationship(back_populates="plantings", lazy="selectin")  # noqa: F821

