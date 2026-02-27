from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DBSession
from app.plants import service
from app.plants.schemas import PlantCreate, PlantRead, PlantUpdate

router = APIRouter(prefix="/api/plants", tags=["plants"])


@router.get("/", response_model=list[PlantRead])
async def list_plants(
    user: CurrentUser,
    db: DBSession,
    search: str | None = Query(default=None, min_length=1),
):
    """List all plants, optionally filtered by search query."""
    if search:
        return await service.search_plants(db, search)
    return await service.get_all_plants(db)


@router.post("/", response_model=PlantRead, status_code=status.HTTP_201_CREATED)
async def create_plant(data: PlantCreate, user: CurrentUser, db: DBSession):
    return await service.create_plant(db, data)


@router.get("/{plant_id}", response_model=PlantRead)
async def get_plant(plant_id: int, user: CurrentUser, db: DBSession):
    plant = await service.get_plant_by_id(db, plant_id)
    if plant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    return plant


@router.patch("/{plant_id}", response_model=PlantRead)
async def update_plant(plant_id: int, data: PlantUpdate, user: CurrentUser, db: DBSession):
    plant = await service.get_plant_by_id(db, plant_id)
    if plant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    return await service.update_plant(db, plant, data)


@router.delete("/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plant(plant_id: int, user: CurrentUser, db: DBSession):
    plant = await service.get_plant_by_id(db, plant_id)
    if plant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    await service.delete_plant(db, plant)

