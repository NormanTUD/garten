"""REST endpoints for valves, schedules, state commands and the poll endpoint.

The ``/api/device/valves`` routes are called by the controller (e.g.
Raspberry Pi with relays); they authenticate with the per-device API key.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import AdminUser, CurrentUser, DBSession
from app.devices.models import Device
from app.devices.security import get_current_device
from app.valves import service
from app.valves.schemas import (
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
    ValveCreate,
    ValveEventRead,
    ValvePollResponse,
    ValveRead,
    ValveStateCommand,
    ValveStateReport,
    ValveUpdate,
)

router = APIRouter(prefix="/api/valves", tags=["valves"])
device_router = APIRouter(prefix="/api/device/valves", tags=["device-valves"])


# ─── Admin: valves CRUD ──────────────────────────────────────────────


@router.post("/", response_model=ValveRead, status_code=status.HTTP_201_CREATED)
async def create_valve(data: ValveCreate, admin: AdminUser, db: DBSession):
    valve = await service.create_valve(db, data)
    await db.commit()
    return valve


@router.get("/", response_model=list[ValveRead])
async def list_valves(
    user: CurrentUser, db: DBSession, active_only: bool = Query(default=False)
):
    return await service.list_valves(db, active_only=active_only)


@router.get("/{valve_id}", response_model=ValveRead)
async def get_valve(valve_id: int, user: CurrentUser, db: DBSession):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    return valve


@router.patch("/{valve_id}", response_model=ValveRead)
async def update_valve(
    valve_id: int, data: ValveUpdate, admin: AdminUser, db: DBSession
):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    return await service.update_valve(db, valve, data)


@router.delete("/{valve_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_valve(valve_id: int, admin: AdminUser, db: DBSession):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    await service.delete_valve(db, valve)
    await db.commit()


# ─── Manual state commands (admin) ──────────────────────────────────


@router.post("/{valve_id}/command", response_model=ValveEventRead)
async def command_valve(
    valve_id: int,
    cmd: ValveStateCommand,
    user: CurrentUser,
    db: DBSession,
):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    event = await service.command_valve(
        db, valve, cmd, triggered_by="manual", triggered_by_id=user.id
    )
    await db.commit()
    return event


# ─── Schedules ───────────────────────────────────────────────────────


@router.post(
    "/{valve_id}/schedules",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    valve_id: int, data: ScheduleCreate, admin: AdminUser, db: DBSession
):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    sched = await service.create_schedule(db, valve_id, data)
    await db.commit()
    return sched


@router.get("/{valve_id}/schedules", response_model=list[ScheduleRead])
async def list_schedules(valve_id: int, user: CurrentUser, db: DBSession):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    return await service.list_schedules_for_valve(db, valve_id)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleRead)
async def update_schedule(
    schedule_id: int, data: ScheduleUpdate, admin: AdminUser, db: DBSession
):
    sched = await service.get_schedule(db, schedule_id)
    if sched is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return await service.update_schedule(db, sched, data)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, admin: AdminUser, db: DBSession):
    sched = await service.get_schedule(db, schedule_id)
    if sched is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    await service.delete_schedule(db, sched)
    await db.commit()


# ─── Events ──────────────────────────────────────────────────────────


@router.get("/{valve_id}/events", response_model=list[ValveEventRead])
async def list_valve_events(
    valve_id: int,
    user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    valve = await service.get_valve(db, valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    return await service.list_events(db, valve_id=valve_id, limit=limit, offset=offset)


# ─── Device-side: poll every 1 minute ───────────────────────────────


@device_router.get("/poll", response_model=ValvePollResponse)
async def device_poll_valves(
    device: Annotated[Device, Depends(get_current_device)],
    db: DBSession,
):
    """Controller polls this endpoint at ~1/min to fetch the desired state
    of every valve attached to *this* device."""
    valves = await service.get_valve_for_device(db, device.id)
    entries = service.build_poll_entries(valves)
    return ValvePollResponse(server_time=datetime.now(UTC), entries=entries)


@device_router.post("/report", response_model=ValveEventRead)
async def device_report_state(
    data: ValveStateReport,
    device: Annotated[Device, Depends(get_current_device)],
    db: DBSession,
):
    """Controller confirms the physical state it has actually applied."""
    valve = await service.get_valve(db, data.valve_id)
    if valve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Valve not found")
    if valve.device_id != device.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Valve does not belong to this device",
        )
    event = await service.apply_controller_report(
        db, valve, data.current_state, data.water_amount_liters
    )
    await db.commit()
    return event
