from fastapi import APIRouter, HTTPException, status

from app.beds import service
from app.beds.schemas import (
    BedCreate,
    BedPlantingCreate,
    BedPlantingRead,
    BedPlantingUpdate,
    BedRead,
    BedUpdate,
)
from app.dependencies import CurrentUser, DBSession
from app.garden.service import get_garden_by_id
from app.plants.service import get_plant_by_id

router = APIRouter(prefix="/api/beds", tags=["beds"])
planting_router = APIRouter(prefix="/api/plantings", tags=["plantings"])


# ─── Beds ─────────────────────────────────────────────────────────

@router.get("/", response_model=list[BedRead])
async def list_beds(garden_id: int, user: CurrentUser, db: DBSession):
    """List all beds for a garden."""
    garden = await get_garden_by_id(db, garden_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garden not found")
    beds = await service.get_beds_by_garden(db, garden_id)
    return [_bed_to_read(b) for b in beds]


@router.post("/", response_model=BedRead, status_code=status.HTTP_201_CREATED)
async def create_bed(data: BedCreate, user: CurrentUser, db: DBSession):
    garden = await get_garden_by_id(db, data.garden_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garden not found")
    bed = await service.create_bed(db, data)
    return _bed_to_read(bed)


@router.get("/{bed_id}", response_model=BedRead)
async def get_bed(bed_id: int, user: CurrentUser, db: DBSession):
    bed = await service.get_bed_by_id(db, bed_id)
    if bed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    return _bed_to_read(bed)


@router.patch("/{bed_id}", response_model=BedRead)
async def update_bed(bed_id: int, data: BedUpdate, user: CurrentUser, db: DBSession):
    bed = await service.get_bed_by_id(db, bed_id)
    if bed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    updated = await service.update_bed(db, bed, data)
    return _bed_to_read(updated)


@router.delete("/{bed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bed(bed_id: int, user: CurrentUser, db: DBSession):
    bed = await service.get_bed_by_id(db, bed_id)
    if bed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    await service.delete_bed(db, bed)


def _bed_to_read(bed: "Bed") -> dict:
    """Convert Bed model to read schema, parsing geometry JSON."""
    import json
    data = {
        "id": bed.id,
        "garden_id": bed.garden_id,
        "name": bed.name,
        "description": bed.description,
        "geometry": json.loads(bed.geometry) if bed.geometry else None,
        "area_sqm": bed.area_sqm,
        "soil_type": bed.soil_type,
        "sun_exposure": bed.sun_exposure,
        "created_at": bed.created_at,
    }
    return data

# ─── Bed Plantings ────────────────────────────────────────────────

@planting_router.get("/", response_model=list[BedPlantingRead])
async def list_plantings(bed_id: int, user: CurrentUser, db: DBSession):
    """List all plantings for a bed."""
    bed = await service.get_bed_by_id(db, bed_id)
    if bed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    return await service.get_plantings_by_bed(db, bed_id)


@planting_router.post("/", response_model=BedPlantingRead, status_code=status.HTTP_201_CREATED)
async def create_planting(data: BedPlantingCreate, user: CurrentUser, db: DBSession):
    bed = await service.get_bed_by_id(db, data.bed_id)
    if bed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    plant = await get_plant_by_id(db, data.plant_id)
    if plant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    planting = await service.create_planting(db, data)
    # Refresh to load plant relationship
    await db.refresh(planting)
    return planting


@planting_router.get("/{planting_id}", response_model=BedPlantingRead)
async def get_planting(planting_id: int, user: CurrentUser, db: DBSession):
    planting = await service.get_planting_by_id(db, planting_id)
    if planting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planting not found")
    return planting


@planting_router.patch("/{planting_id}", response_model=BedPlantingRead)
async def update_planting(
    planting_id: int, data: BedPlantingUpdate, user: CurrentUser, db: DBSession
):
    planting = await service.get_planting_by_id(db, planting_id)
    if planting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planting not found")
    updated = await service.update_planting(db, planting, data)
    await db.refresh(updated)
    return updated


@planting_router.delete("/{planting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planting(planting_id: int, user: CurrentUser, db: DBSession):
    planting = await service.get_planting_by_id(db, planting_id)
    if planting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planting not found")
    await service.delete_planting(db, planting)

