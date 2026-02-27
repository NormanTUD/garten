from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.watering.models import FertilizingEvent, WateringEvent
from app.watering.schemas import (
    FertilizingEventCreate,
    FertilizingEventUpdate,
    WateringEventCreate,
    WateringEventUpdate,
)


# ─── Watering Events ─────────────────────────────────────────────

async def get_all_watering_events(
    db: AsyncSession,
    *,
    bed_id: int | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[WateringEvent]:
    stmt = select(WateringEvent).order_by(WateringEvent.started_at.desc())

    if bed_id is not None:
        stmt = stmt.where(WateringEvent.bed_id == bed_id)
    if user_id is not None:
        stmt = stmt.where(WateringEvent.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(WateringEvent.started_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(WateringEvent.started_at <= date_to)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_watering_event_by_id(db: AsyncSession, event_id: int) -> WateringEvent | None:
    result = await db.execute(select(WateringEvent).where(WateringEvent.id == event_id))
    return result.scalar_one_or_none()


async def create_watering_event(
    db: AsyncSession, user_id: int, data: WateringEventCreate
) -> WateringEvent:
    event = WateringEvent(user_id=user_id, **data.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def update_watering_event(
    db: AsyncSession, event: WateringEvent, data: WateringEventUpdate
) -> WateringEvent:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    await db.flush()
    await db.refresh(event)
    return event


async def delete_watering_event(db: AsyncSession, event: WateringEvent) -> None:
    await db.delete(event)
    await db.flush()


# ─── Fertilizing Events ──────────────────────────────────────────

async def get_all_fertilizing_events(
    db: AsyncSession,
    *,
    bed_id: int | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FertilizingEvent]:
    stmt = select(FertilizingEvent).order_by(FertilizingEvent.event_date.desc())

    if bed_id is not None:
        stmt = stmt.where(FertilizingEvent.bed_id == bed_id)
    if user_id is not None:
        stmt = stmt.where(FertilizingEvent.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(FertilizingEvent.event_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(FertilizingEvent.event_date <= date_to)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_fertilizing_event_by_id(db: AsyncSession, event_id: int) -> FertilizingEvent | None:
    result = await db.execute(
        select(FertilizingEvent).where(FertilizingEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def create_fertilizing_event(
    db: AsyncSession, user_id: int, data: FertilizingEventCreate
) -> FertilizingEvent:
    event = FertilizingEvent(user_id=user_id, **data.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def update_fertilizing_event(
    db: AsyncSession, event: FertilizingEvent, data: FertilizingEventUpdate
) -> FertilizingEvent:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    await db.flush()
    await db.refresh(event)
    return event


async def delete_fertilizing_event(db: AsyncSession, event: FertilizingEvent) -> None:
    await db.delete(event)
    await db.flush()

