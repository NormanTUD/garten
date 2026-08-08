"""REST endpoints for the MAC-address allowlist.

Used by cameras and other IoT devices to gate alerts: only events from
*unknown* MAC addresses raise notifications.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.apikeys.security import Principal, require_scope
from app.auth.permissions import Scope
from app.dependencies import AdminUser, CurrentUser, DBSession
from app.network import service
from app.network.schemas import (
    MacLookupResponse,
    NetworkDeviceCreate,
    NetworkDeviceRead,
    NetworkDeviceUpdate,
)

router = APIRouter(prefix="/api/network", tags=["network"])


@router.post(
    "/devices",
    response_model=NetworkDeviceRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_device(data: NetworkDeviceCreate, admin: AdminUser, db: DBSession):
    try:
        device = await service.create_device(db, data)
    except ValueError as err:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(err)) from err
    await db.commit()
    return device


@router.get("/devices", response_model=list[NetworkDeviceRead])
async def list_devices(
    user: CurrentUser,
    db: DBSession,
    active_only: bool = Query(default=True),
    trusted_only: bool = Query(default=False),
    device_type: str | None = Query(default=None),
):
    return await service.list_devices(
        db,
        active_only=active_only,
        trusted_only=trusted_only,
        device_type=device_type,
    )


@router.get("/devices/{device_id}", response_model=NetworkDeviceRead)
async def get_device(device_id: int, admin: AdminUser, db: DBSession):
    device = await service.get_device(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.patch("/devices/{device_id}", response_model=NetworkDeviceRead)
async def update_device(
    device_id: int, data: NetworkDeviceUpdate, admin: AdminUser, db: DBSession
):
    device = await service.get_device(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return await service.update_device(db, device, data)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: int, admin: AdminUser, db: DBSession):
    device = await service.get_device(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    await service.delete_device(db, device)
    await db.commit()


@router.get("/lookup", response_model=MacLookupResponse)
async def lookup_mac(
    mac: str = Query(..., min_length=11, max_length=17),
    principal: Annotated[
        Principal,
        Depends(require_scope(Scope.NETWORK_READ.value)),
    ] = None,
    db: DBSession = None,
):
    """Quick allowlist check (used by camera/IoT devices & the frontend).

    Requires the ``network:read`` scope. Admins and regular users with
    the default scope set pass automatically; API keys must include it.

    ``is_trusted`` in the response reflects the *effective* trust value:
    a device that exists but is inactive (or explicitly untrusted) returns
    ``is_trusted=False`` so that cameras/IoT always raise an alert.
    """
    device = await service.get_by_mac(db, mac)
    if device is None:
        return MacLookupResponse(
            mac_address=mac.upper(),
            is_trusted=False,
            is_active=False,
            device_name=None,
            owner_user_id=None,
            known_person_id=None,
        )
    return MacLookupResponse(
        mac_address=device.mac_address,
        is_trusted=service.is_mac_trusted(device),
        is_active=device.is_active,
        device_name=device.name,
        owner_user_id=device.owner_user_id,
        known_person_id=device.known_person_id,
    )
