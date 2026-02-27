from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.plants.models import Plant
from app.plants.schemas import PlantCreate, PlantUpdate


async def get_all_plants(db: AsyncSession) -> list[Plant]:
    result = await db.execute(select(Plant).order_by(Plant.name))
    return list(result.scalars().all())


async def get_plant_by_id(db: AsyncSession, plant_id: int) -> Plant | None:
    result = await db.execute(select(Plant).where(Plant.id == plant_id))
    return result.scalar_one_or_none()


async def search_plants(db: AsyncSession, query: str) -> list[Plant]:
    """Search plants by name or variety (case-insensitive)."""
    result = await db.execute(
        select(Plant)
        .where(
            Plant.name.ilike(f"%{query}%") | Plant.variety.ilike(f"%{query}%")
        )
        .order_by(Plant.name)
    )
    return list(result.scalars().all())


async def create_plant(db: AsyncSession, data: PlantCreate) -> Plant:
    plant = Plant(**data.model_dump())
    db.add(plant)
    await db.flush()
    await db.refresh(plant)
    return plant


async def update_plant(db: AsyncSession, plant: Plant, data: PlantUpdate) -> Plant:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plant, field, value)
    await db.flush()
    await db.refresh(plant)
    return plant


async def delete_plant(db: AsyncSession, plant: Plant) -> None:
    await db.delete(plant)
    await db.flush()

