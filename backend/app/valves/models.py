"""Valve (water hose) models, schedules and state events."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Valve(Base):
    """A controllable water valve (physical hose)."""

    __tablename__ = "valves"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    bed_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hardware_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    gpio_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normally_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    flow_liters_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # State (mirrored from device; updated via polling endpoint)
    current_state: Mapped[str] = mapped_column(String(10), nullable=False, default="closed")
    desired_state: Mapped[str] = mapped_column(String(10), nullable=False, default="closed")
    state_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    device: Mapped[Device | None] = relationship(back_populates="valves")  # noqa: F821
    schedules: Mapped[list[ValveSchedule]] = relationship(
        back_populates="valve",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[list[ValveEvent]] = relationship(
        back_populates="valve",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ValveSchedule(Base):
    """Recurring schedule that opens a valve for a defined duration."""

    __tablename__ = "valve_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    valve_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("valves.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Time of day in "HH:MM"
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    # JSON list of weekdays: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    days_of_week: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    valve: Mapped[Valve] = relationship(back_populates="schedules")


class ValveEvent(Base):
    """A single state change of a valve (open / close / confirmation)."""

    __tablename__ = "valve_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    valve_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("valves.id", ondelete="CASCADE"), nullable=False, index=True
    )
    new_state: Mapped[str] = mapped_column(String(10), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(30), nullable=False)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    water_amount_liters: Mapped[float | None] = mapped_column(Float, nullable=True)

    valve: Mapped[Valve] = relationship(back_populates="events")
