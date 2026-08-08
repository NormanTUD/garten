"""Network allowlist: known MAC addresses for cameras, IoT and members."""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to AA:BB:CC:DD:EE:FF (uppercase, colon-separated)."""
    if not mac:
        return mac
    cleaned = re.sub(r"[-:.]", "", mac.strip()).upper()
    if len(cleaned) != 12 or not all(c in "0123456789ABCDEF" for c in cleaned):
        raise ValueError(f"Invalid MAC address: {mac!r}")
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))


class NetworkDevice(Base):
    """Known network device (camera, IoT, sensor or member device)."""

    __tablename__ = "network_devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    owner_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    known_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("known_persons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_trusted: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    @staticmethod
    def is_valid_mac(mac: str) -> bool:
        return bool(MAC_REGEX.match(mac.strip()))
