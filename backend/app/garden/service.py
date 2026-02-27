from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.garden.models import Garden
from app.garden.schemas import GardenCreate, GardenUpdate


async def get_all_gardens(db: AsyncSession) -> list[Garden]:
    result = await db.execute(select(Garden).order_by(Garden.name))
    return list(result.scalars().all())


async def get_garden_by_id(db: AsyncSession, garden_id: int) -> Garden | None:
    result = await db.execute(select(Garden).where(Garden.id == garden_id))
    return result.scalar_one_or_none()


async def create_garden(db: AsyncSession, data: GardenCreate) -> Garden:
    garden = Garden(**data.model_dump())
    db.add(garden)
    await db.flush()
    await db.refresh(garden)
    return garden


async def update_garden(db: AsyncSession, garden: Garden, data: GardenUpdate) -> Garden:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(garden, field, value)
    await db.flush()
    await db.refresh(garden)
    return garden


async def delete_garden(db: AsyncSession, garden: Garden) -> None:
    await db.delete(garden)
    await db.flush()

