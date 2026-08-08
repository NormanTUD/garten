"""IoT device models: cameras, valves, sensors."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Device(Base):
    """A registered IoT device (camera, valve controller, sensor, …)."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    hardware_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    events: Mapped[list[DeviceEvent]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    camera: Mapped[Camera | None] = relationship(  # noqa: F821
        back_populates="device",
        cascade="all, delete-orphan",
        uselist=False,
    )
    valves: Mapped[list[Valve]] = relationship(  # noqa: F821
        back_populates="device",
        cascade="all, delete-orphan",
    )


class DeviceEvent(Base):
    """Generic event log entry from a device."""

    __tablename__ = "device_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    device: Mapped[Device] = relationship(back_populates="events")
