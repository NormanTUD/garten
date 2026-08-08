"""Service layer for valves and their schedules."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.valves.models import Valve, ValveEvent, ValveSchedule
from app.valves.schemas import (
    ScheduleCreate,
    ScheduleUpdate,
    ValveCreate,
    ValvePollEntry,
    ValveStateCommand,
    ValveUpdate,
)

logger = logging.getLogger("gartenapp.valves")

STATE_OPEN = "open"
STATE_CLOSED = "closed"
STATE_ERROR = "error"


# ─── Valves ──────────────────────────────────────────────────────────


async def create_valve(db: AsyncSession, data: ValveCreate) -> Valve:
    valve = Valve(**data.model_dump())
    db.add(valve)
    await db.flush()
    await db.refresh(valve)
    return valve


async def get_valve(db: AsyncSession, valve_id: int) -> Valve | None:
    result = await db.execute(select(Valve).where(Valve.id == valve_id))
    return result.scalar_one_or_none()


async def list_valves(db: AsyncSession, active_only: bool = False) -> list[Valve]:
    stmt = select(Valve).order_by(Valve.name)
    if active_only:
        stmt = stmt.where(Valve.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_valve(db: AsyncSession, valve: Valve, data: ValveUpdate) -> Valve:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(valve, field, value)
    await db.flush()
    await db.refresh(valve)
    return valve


async def delete_valve(db: AsyncSession, valve: Valve) -> None:
    await db.delete(valve)
    await db.flush()


# ─── Schedules ───────────────────────────────────────────────────────


async def create_schedule(db: AsyncSession, valve_id: int, data: ScheduleCreate) -> ValveSchedule:
    schedule = ValveSchedule(valve_id=valve_id, **data.model_dump())
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)
    return schedule


async def list_schedules_for_valve(db: AsyncSession, valve_id: int) -> list[ValveSchedule]:
    result = await db.execute(
        select(ValveSchedule)
        .where(ValveSchedule.valve_id == valve_id)
        .order_by(ValveSchedule.start_time)
    )
    return list(result.scalars().all())


async def get_schedule(db: AsyncSession, schedule_id: int) -> ValveSchedule | None:
    result = await db.execute(
        select(ValveSchedule).where(ValveSchedule.id == schedule_id)
    )
    return result.scalar_one_or_none()


async def update_schedule(
    db: AsyncSession, schedule: ValveSchedule, data: ScheduleUpdate
) -> ValveSchedule:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    await db.flush()
    await db.refresh(schedule)
    return schedule


async def delete_schedule(db: AsyncSession, schedule: ValveSchedule) -> None:
    await db.delete(schedule)
    await db.flush()


async def list_active_schedules(db: AsyncSession) -> list[ValveSchedule]:
    result = await db.execute(
        select(ValveSchedule).where(ValveSchedule.is_active.is_(True))
    )
    return list(result.scalars().all())


# ─── State commands & polling ───────────────────────────────────────


async def command_valve(
    db: AsyncSession,
    valve: Valve,
    cmd: ValveStateCommand,
    triggered_by: str,
    triggered_by_id: int | None,
) -> ValveEvent:
    """Apply a state command. Records a ValveEvent."""
    now = datetime.now(UTC)

    # If we are closing, close out any open event first
    if cmd.new_state == STATE_CLOSED and valve.current_state == STATE_OPEN:
        await _close_open_event(db, valve, now)

    valve.desired_state = cmd.new_state
    valve.state_changed_at = now

    event = ValveEvent(
        valve_id=valve.id,
        new_state=cmd.new_state,
        triggered_by=triggered_by,
        triggered_by_id=triggered_by_id,
        reason=cmd.reason,
        opened_at=now if cmd.new_state == STATE_OPEN else now,
    )
    db.add(event)

    # For schedules: schedule the close after duration
    if cmd.new_state == STATE_OPEN and cmd.duration_seconds:
        from app.valves.scheduler import schedule_close_after
        schedule_close_after(db, valve, cmd.duration_seconds, triggered_by=triggered_by)
    # We do *not* flip current_state here; the physical controller
    # confirms via the poll endpoint, and only then we mark as actually open.

    await db.flush()
    await db.refresh(event)
    return event


async def _close_open_event(
    db: AsyncSession, valve: Valve, closed_at: datetime
) -> ValveEvent | None:
    result = await db.execute(
        select(ValveEvent)
        .where(ValveEvent.valve_id == valve.id)
        .where(ValveEvent.new_state == STATE_OPEN)
        .where(ValveEvent.closed_at.is_(None))
        .order_by(ValveEvent.opened_at.desc())
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None
    event.closed_at = closed_at
    if valve.flow_liters_per_minute:
        duration_minutes = (closed_at - event.opened_at).total_seconds() / 60.0
        event.water_amount_liters = round(duration_minutes * valve.flow_liters_per_minute, 2)
    await db.flush()
    await db.refresh(event)
    return event


async def apply_controller_report(
    db: AsyncSession,
    valve: Valve,
    current_state: str,
    water_amount_liters: float | None,
) -> ValveEvent:
    """The controller (Pi) confirms the actual physical state via the
    report endpoint. We update the DB and close any open event.
    """
    now = datetime.now(UTC)
    valve.current_state = current_state
    valve.state_changed_at = now

    if current_state == STATE_CLOSED and valve.desired_state == STATE_CLOSED:
        # close out the event
        await _close_open_event(db, valve, now)

    event = ValveEvent(
        valve_id=valve.id,
        new_state=current_state,
        triggered_by="controller",
        opened_at=now,
        closed_at=now if current_state == STATE_CLOSED else None,
        water_amount_liters=water_amount_liters,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


def build_poll_entries(valves: list[Valve]) -> list[ValvePollEntry]:
    """Compute the desired state for every valve."""
    entries: list[ValvePollEntry] = []
    for v in valves:
        if not v.is_active:
            continue
        entries.append(
            ValvePollEntry(
                valve_id=v.id,
                hardware_id=v.hardware_id,
                desired_state=v.desired_state,
            )
        )
    return entries


async def list_events(
    db: AsyncSession,
    valve_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ValveEvent]:
    stmt = select(ValveEvent).order_by(ValveEvent.opened_at.desc())
    if valve_id is not None:
        stmt = stmt.where(ValveEvent.valve_id == valve_id)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_valve_for_hardware(
    db: AsyncSession, hardware_id: str
) -> Valve | None:
    result = await db.execute(select(Valve).where(Valve.hardware_id == hardware_id))
    return result.scalar_one_or_none()


async def get_valve_for_device(db: AsyncSession, device_id: int) -> list[Valve]:
    result = await db.execute(select(Valve).where(Valve.device_id == device_id))
    return list(result.scalars().all())
