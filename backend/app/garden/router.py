from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DBSession
from app.garden import service
from app.garden.schemas import GardenCreate, GardenRead, GardenUpdate

router = APIRouter(prefix="/api/gardens", tags=["gardens"])


@router.get("/", response_model=list[GardenRead])
async def list_gardens(user: CurrentUser, db: DBSession):
    return await service.get_all_gardens(db)


@router.post("/", response_model=GardenRead, status_code=status.HTTP_201_CREATED)
async def create_garden(data: GardenCreate, user: CurrentUser, db: DBSession):
    return await service.create_garden(db, data)


@router.get("/{garden_id}", response_model=GardenRead)
async def get_garden(garden_id: int, user: CurrentUser, db: DBSession):
    garden = await service.get_garden_by_id(db, garden_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garden not found")
    return garden


@router.patch("/{garden_id}", response_model=GardenRead)
async def update_garden(garden_id: int, data: GardenUpdate, user: CurrentUser, db: DBSession):
    garden = await service.get_garden_by_id(db, garden_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garden not found")
    return await service.update_garden(db, garden, data)


@router.delete("/{garden_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_garden(garden_id: int, user: CurrentUser, db: DBSession):
    garden = await service.get_garden_by_id(db, garden_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garden not found")
    await service.delete_garden(db, garden)

