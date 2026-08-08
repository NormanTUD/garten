"""Service layer for device management."""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import Device, DeviceEvent
from app.devices.schemas import DeviceEventCreate, DeviceRegister, DeviceUpdate
from app.devices.security import generate_api_key

logger = logging.getLogger("gartenapp.devices")


def hash_api_key(api_key: str) -> str:
    """Hash an API key with SHA-256 for at-rest storage.

    SHA-256 is acceptable here because the input space is 256 bits of
    randomness from ``secrets.token_urlsafe(32)`` – brute force is
    computationally infeasible. We don't need bcrypt's slow hash.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def register_device(
    db: AsyncSession, data: DeviceRegister, created_by_id: int | None = None
) -> tuple[Device, str]:
    """Register a new device. Returns ``(device, api_key)`` – the key is shown
    to the admin only at creation time and never again."""
    api_key = generate_api_key()
    device = Device(
        name=data.name,
        device_type=data.device_type,
        hardware_id=data.hardware_id,
        location=data.location,
        description=data.description,
        api_key_hash=hash_api_key(api_key),
        created_by_id=created_by_id,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)
    logger.info("Device registered: %s (type=%s)", device.name, device.device_type)
    return device, api_key


async def get_device_by_api_key(db: AsyncSession, api_key: str) -> Device | None:
    key_hash = hash_api_key(api_key)
    result = await db.execute(select(Device).where(Device.api_key_hash == key_hash))
    return result.scalar_one_or_none()


async def get_device_by_id(db: AsyncSession, device_id: int) -> Device | None:
    result = await db.execute(select(Device).where(Device.id == device_id))
    return result.scalar_one_or_none()


async def list_devices(
    db: AsyncSession, device_type: str | None = None, active_only: bool = False
) -> list[Device]:
    stmt = select(Device).order_by(Device.registered_at.desc())
    if device_type:
        stmt = stmt.where(Device.device_type == device_type)
    if active_only:
        stmt = stmt.where(Device.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_device(
    db: AsyncSession, device: Device, data: DeviceUpdate
) -> Device:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    await db.flush()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device: Device) -> None:
    await db.delete(device)
    await db.flush()


async def record_event(
    db: AsyncSession,
    device: Device,
    data: DeviceEventCreate,
) -> DeviceEvent:
    event = DeviceEvent(
        device_id=device.id,
        event_type=data.event_type,
        severity=data.severity,
        payload=data.payload,
        message=data.message,
        occurred_at=data.occurred_at or datetime.now(UTC),
    )
    db.add(event)
    device.last_seen_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(event)
    return event


async def list_events(
    db: AsyncSession,
    device_id: int | None = None,
    event_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[DeviceEvent]:
    stmt = select(DeviceEvent).order_by(DeviceEvent.received_at.desc())
    if device_id is not None:
        stmt = stmt.where(DeviceEvent.device_id == device_id)
    if event_type:
        stmt = stmt.where(DeviceEvent.event_type == event_type)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def record_heartbeat(
    db: AsyncSession,
    device: Device,
    status: str,
    metrics: dict | None,
) -> Device:
    device.last_seen_at = datetime.now(UTC)
    await db.flush()
    # Log a heartbeat event (rate-limited by caller if needed)
    event = DeviceEvent(
        device_id=device.id,
        event_type="heartbeat",
        severity="info" if status == "ok" else "warning",
        payload={"status": status, **(metrics or {})},
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return device
