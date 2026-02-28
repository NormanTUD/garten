from datetime import date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


class GardenDutyConfig(Base):
    """Yearly configuration for garden duty hours and compensation rate."""

    __tablename__ = "garden_duty_config"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, unique=True, index=True)
    total_hours = Column(Float, nullable=False)  # Total hours for the whole garden
    hourly_rate_cents = Column(Integer, nullable=False)  # Compensation per hour in cents
    notes = Column(Text, nullable=True)


class GardenDutyAssignment(Base):
    """Per-member hour assignment for a given year. Allows custom splits."""

    __tablename__ = "garden_duty_assignment"
    __table_args__ = (
        UniqueConstraint("user_id", "year", name="uq_duty_assignment_user_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    assigned_hours = Column(Float, nullable=False)  # This person's share
    notes = Column(Text, nullable=True)  # e.g. "Tausch mit Max"

    user = relationship("User", lazy="joined")


class GardenDutyLog(Base):
    """Individual duty work log entry."""

    __tablename__ = "garden_duty_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)  # Supports 0.5h increments
    description = Column(Text, nullable=True)
    confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id], lazy="joined")

