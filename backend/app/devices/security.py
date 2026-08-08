"""Device & API-key authentication for IoT endpoints (cameras, valves, sensors)."""
from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.devices import service
from app.devices.models import Device

DBSession = Annotated[AsyncSession, Depends(get_async_session)]


def generate_api_key() -> str:
    """Generate a long, URL-safe API key for a device."""
    return secrets.token_urlsafe(32)


async def _authenticate_device(
    authorization: str | None,
    x_device_key: str | None,
    db: AsyncSession,
) -> Device:
    """Resolve the calling device from either ``Authorization: Bearer <key>``
    or the ``X-Device-Key`` header.

    Raises 401 if neither header is present or the key is unknown.
    """
    key: str | None = None
    if x_device_key:
        key = x_device_key.strip()
    elif authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value:
            key = value.strip()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device credentials required (X-Device-Key or Bearer token)",
            headers={"WWW-Authenticate": "Device"},
        )

    device = await service.get_device_by_api_key(db, key)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
            headers={"WWW-Authenticate": "Device"},
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is deactivated",
        )
    return device


async def get_current_device(
    db: DBSession,
    x_device_key: Annotated[str | None, Header(alias="X-Device-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Device:
    """FastAPI dependency: returns the authenticated :class:`Device`."""
    return await _authenticate_device(authorization, x_device_key, db)
