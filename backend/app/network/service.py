"""Service layer for the network allowlist."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.network.models import NetworkDevice, normalize_mac
from app.network.schemas import NetworkDeviceCreate, NetworkDeviceUpdate

logger = logging.getLogger("gartenapp.network")


async def create_device(db: AsyncSession, data: NetworkDeviceCreate) -> NetworkDevice:
    device = NetworkDevice(
        mac_address=data.mac_address,
        name=data.name,
        device_type=data.device_type,
        owner_user_id=data.owner_user_id,
        known_person_id=data.known_person_id,
        notes=data.notes,
        is_trusted=data.is_trusted,
    )
    db.add(device)
    try:
        await db.flush()
    except IntegrityError as err:
        await db.rollback()
        raise ValueError(f"MAC {data.mac_address} already in allowlist") from err
    await db.refresh(device)
    return device


async def get_device(db: AsyncSession, device_id: int) -> NetworkDevice | None:
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    return result.scalar_one_or_none()


async def get_by_mac(db: AsyncSession, mac_address: str) -> NetworkDevice | None:
    try:
        normalized = normalize_mac(mac_address)
    except ValueError:
        return None
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.mac_address == normalized)
    )
    return result.scalar_one_or_none()


async def list_devices(
    db: AsyncSession,
    active_only: bool = True,
    trusted_only: bool = False,
    device_type: str | None = None,
) -> list[NetworkDevice]:
    stmt = select(NetworkDevice).order_by(NetworkDevice.name)
    if active_only:
        stmt = stmt.where(NetworkDevice.is_active.is_(True))
    if trusted_only:
        stmt = stmt.where(NetworkDevice.is_trusted.is_(True))
    if device_type:
        stmt = stmt.where(NetworkDevice.device_type == device_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_device(
    db: AsyncSession, device: NetworkDevice, data: NetworkDeviceUpdate
) -> NetworkDevice:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    await db.flush()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device: NetworkDevice) -> None:
    await db.delete(device)
    await db.flush()


async def record_seen(db: AsyncSession, device: NetworkDevice) -> None:
    device.last_seen_at = datetime.now(UTC)
    await db.flush()


def is_mac_trusted(device: NetworkDevice | None) -> bool:
    """Return True only for active & explicitly trusted entries."""
    return bool(device and device.is_active and device.is_trusted)
