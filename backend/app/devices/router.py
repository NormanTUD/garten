"""REST endpoints for IoT device management.

Devices authenticate with their per-device API key, supplied via
``X-Device-Key`` (preferred) or ``Authorization: Bearer <key>``.

Admins manage the device lifecycle via JWT auth.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import AdminUser, DBSession
from app.devices import service
from app.devices.models import Device
from app.devices.schemas import (
    DeviceCreated,
    DeviceEventCreate,
    DeviceEventRead,
    DeviceHeartbeat,
    DeviceRead,
    DeviceRegister,
    DeviceUpdate,
)
from app.devices.security import get_current_device

router = APIRouter(prefix="/api/devices", tags=["devices"])


# ─── Admin: device lifecycle ─────────────────────────────────────────


@router.post("/", response_model=DeviceCreated, status_code=status.HTTP_201_CREATED)
async def register_new_device(data: DeviceRegister, admin: AdminUser, db: DBSession):
    """Register a new IoT device. The API key is returned **once**."""
    device, api_key = await service.register_device(db, data, created_by_id=admin.id)
    await db.commit()
    base = DeviceRead.model_validate(device).model_dump()
    return DeviceCreated(**base, api_key=api_key)


@router.get("/", response_model=list[DeviceRead])
async def list_devices(
    admin: AdminUser,
    db: DBSession,
    device_type: str | None = Query(default=None),
    active_only: bool = Query(default=False),
):
    return await service.list_devices(db, device_type=device_type, active_only=active_only)


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(device_id: int, admin: AdminUser, db: DBSession):
    device = await service.get_device_by_id(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: int, data: DeviceUpdate, admin: AdminUser, db: DBSession
):
    device = await service.get_device_by_id(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return await service.update_device(db, device, data)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: int, admin: AdminUser, db: DBSession):
    device = await service.get_device_by_id(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    await service.delete_device(db, device)
    await db.commit()


# ─── Admin: events ───────────────────────────────────────────────────


@router.get("/events/all", response_model=list[DeviceEventRead])
async def list_all_events(
    admin: AdminUser,
    db: DBSession,
    device_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return await service.list_events(
        db, device_id=device_id, event_type=event_type, limit=limit, offset=offset
    )


@router.get("/{device_id}/events", response_model=list[DeviceEventRead])
async def list_device_events(
    device_id: int,
    admin: AdminUser,
    db: DBSession,
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    device = await service.get_device_by_id(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return await service.list_events(
        db, device_id=device_id, event_type=event_type, limit=limit, offset=offset
    )


# ─── Device-side endpoints (device API-key auth) ─────────────────────


device_router = APIRouter(prefix="/api/device", tags=["device"])


@device_router.get("/me", response_model=DeviceRead)
async def device_whoami(device: Annotated[Device, Depends(get_current_device)]):
    return device


@device_router.post("/heartbeat", response_model=DeviceRead)
async def device_heartbeat(
    data: DeviceHeartbeat,
    device: Annotated[Device, Depends(get_current_device)],
    db: DBSession,
):
    updated = await service.record_heartbeat(db, device, data.status, data.metrics)
    await db.commit()
    return updated


@device_router.post("/events", response_model=DeviceEventRead, status_code=status.HTTP_201_CREATED)
async def device_post_event(
    data: DeviceEventCreate,
    device: Annotated[Device, Depends(get_current_device)],
    db: DBSession,
):
    event = await service.record_event(db, device, data)
    await db.commit()
    return event
