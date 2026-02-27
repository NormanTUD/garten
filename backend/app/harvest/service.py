from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.harvest.models import Harvest
from app.harvest.schemas import HarvestCreate, HarvestUpdate


async def get_all_harvests(
    db: AsyncSession,
    *,
    bed_id: int | None = None,
    plant_id: int | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Harvest]:
    stmt = select(Harvest).order_by(Harvest.date.desc(), Harvest.created_at.desc())

    if bed_id is not None:
        stmt = stmt.where(Harvest.bed_id == bed_id)
    if plant_id is not None:
        stmt = stmt.where(Harvest.plant_id == plant_id)
    if user_id is not None:
        stmt = stmt.where(Harvest.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(Harvest.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Harvest.date <= date_to)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_harvest_by_id(db: AsyncSession, harvest_id: int) -> Harvest | None:
    result = await db.execute(select(Harvest).where(Harvest.id == harvest_id))
    return result.scalar_one_or_none()


async def create_harvest(db: AsyncSession, user_id: int, data: HarvestCreate) -> Harvest:
    harvest = Harvest(
        user_id=user_id,
        **data.model_dump(),
    )
    db.add(harvest)
    await db.flush()
    await db.refresh(harvest)
    return harvest


async def update_harvest(db: AsyncSession, harvest: Harvest, data: HarvestUpdate) -> Harvest:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(harvest, field, value)
    await db.flush()
    await db.refresh(harvest)
    return harvest


async def delete_harvest(db: AsyncSession, harvest: Harvest) -> None:
    await db.delete(harvest)
    await db.flush()

