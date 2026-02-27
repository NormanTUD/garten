from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.beds.service import get_bed_by_id
from app.dependencies import CurrentUser, DBSession
from app.watering import service
from app.watering.schemas import (
    FertilizingEventCreate,
    FertilizingEventRead,
    FertilizingEventUpdate,
    WateringEventCreate,
    WateringEventRead,
    WateringEventUpdate,
)

watering_router = APIRouter(prefix="/api/watering", tags=["watering"])
fertilizing_router = APIRouter(prefix="/api/fertilizing", tags=["fertilizing"])


# ─── Watering Events ─────────────────────────────────────────────

@watering_router.get("/", response_model=list[WateringEventRead])
async def list_watering_events(
    user: CurrentUser,
    db: DBSession,
    bed_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List watering events with optional filters."""
    return await service.get_all_watering_events(
        db,
        bed_id=bed_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@watering_router.post("/", response_model=WateringEventRead, status_code=status.HTTP_201_CREATED)
async def create_watering_event(data: WateringEventCreate, user: CurrentUser, db: DBSession):
    """Create a watering event. user_id is set from JWT automatically."""
    if data.bed_id is not None:
        bed = await get_bed_by_id(db, data.bed_id)
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    event = await service.create_watering_event(db, user.id, data)
    await db.refresh(event)
    return event


@watering_router.get("/{event_id}", response_model=WateringEventRead)
async def get_watering_event(event_id: int, user: CurrentUser, db: DBSession):
    event = await service.get_watering_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Watering event not found"
        )
    return event


@watering_router.patch("/{event_id}", response_model=WateringEventRead)
async def update_watering_event(
    event_id: int, data: WateringEventUpdate, user: CurrentUser, db: DBSession
):
    event = await service.get_watering_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Watering event not found"
        )
    if data.bed_id is not None:
        bed = await get_bed_by_id(db, data.bed_id)
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    updated = await service.update_watering_event(db, event, data)
    await db.refresh(updated)
    return updated


@watering_router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watering_event(event_id: int, user: CurrentUser, db: DBSession):
    event = await service.get_watering_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Watering event not found"
        )
    await service.delete_watering_event(db, event)


# ─── Fertilizing Events ──────────────────────────────────────────

@fertilizing_router.get("/", response_model=list[FertilizingEventRead])
async def list_fertilizing_events(
    user: CurrentUser,
    db: DBSession,
    bed_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List fertilizing events with optional filters."""
    return await service.get_all_fertilizing_events(
        db,
        bed_id=bed_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@fertilizing_router.post(
    "/", response_model=FertilizingEventRead, status_code=status.HTTP_201_CREATED
)
async def create_fertilizing_event(
    data: FertilizingEventCreate, user: CurrentUser, db: DBSession
):
    """Create a fertilizing event. user_id is set from JWT automatically."""
    if data.bed_id is not None:
        bed = await get_bed_by_id(db, data.bed_id)
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    event = await service.create_fertilizing_event(db, user.id, data)
    await db.refresh(event)
    return event


@fertilizing_router.get("/{event_id}", response_model=FertilizingEventRead)
async def get_fertilizing_event(event_id: int, user: CurrentUser, db: DBSession):
    event = await service.get_fertilizing_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fertilizing event not found"
        )
    return event


@fertilizing_router.patch("/{event_id}", response_model=FertilizingEventRead)
async def update_fertilizing_event(
    event_id: int, data: FertilizingEventUpdate, user: CurrentUser, db: DBSession
):
    event = await service.get_fertilizing_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fertilizing event not found"
        )
    if data.bed_id is not None:
        bed = await get_bed_by_id(db, data.bed_id)
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    updated = await service.update_fertilizing_event(db, event, data)
    await db.refresh(updated)
    return updated


@fertilizing_router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fertilizing_event(event_id: int, user: CurrentUser, db: DBSession):
    event = await service.get_fertilizing_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fertilizing event not found"
        )
    await service.delete_fertilizing_event(db, event)

