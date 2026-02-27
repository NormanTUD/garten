from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.beds.service import get_bed_by_id
from app.dependencies import CurrentUser, DBSession
from app.harvest import service
from app.harvest.schemas import HarvestCreate, HarvestRead, HarvestUpdate
from app.plants.service import get_plant_by_id

router = APIRouter(prefix="/api/harvests", tags=["harvests"])


@router.get("/", response_model=list[HarvestRead])
async def list_harvests(
    user: CurrentUser,
    db: DBSession,
    bed_id: int | None = Query(default=None),
    plant_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List harvests with optional filters."""
    return await service.get_all_harvests(
        db,
        bed_id=bed_id,
        plant_id=plant_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=HarvestRead, status_code=status.HTTP_201_CREATED)
async def create_harvest(data: HarvestCreate, user: CurrentUser, db: DBSession):
    """Create a harvest entry. user_id is set from JWT automatically."""
    if data.bed_id is not None:
        bed = await get_bed_by_id(db, data.bed_id)
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    if data.plant_id is not None:
        plant = await get_plant_by_id(db, data.plant_id)
        if plant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    harvest = await service.create_harvest(db, user.id, data)
    await db.refresh(harvest)
    return harvest


@router.get("/{harvest_id}", response_model=HarvestRead)
async def get_harvest(harvest_id: int, user: CurrentUser, db: DBSession):
    harvest = await service.get_harvest_by_id(db, harvest_id)
    if harvest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Harvest not found")
    return harvest


@router.patch("/{harvest_id}", response_model=HarvestRead)
async def update_harvest(
    harvest_id: int, data: HarvestUpdate, user: CurrentUser, db: DBSession
):
    harvest = await service.get_harvest_by_id(db, harvest_id)
    if harvest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Harvest not found")
    if data.bed_id is not None:
        bed = await get_bed_by_id(db, data.bed_id)
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    if data.plant_id is not None:
        plant = await get_plant_by_id(db, data.plant_id)
        if plant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    updated = await service.update_harvest(db, harvest, data)
    await db.refresh(updated)
    return updated


@router.delete("/{harvest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_harvest(harvest_id: int, user: CurrentUser, db: DBSession):
    harvest = await service.get_harvest_by_id(db, harvest_id)
    if harvest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Harvest not found")
    await service.delete_harvest(db, harvest)

