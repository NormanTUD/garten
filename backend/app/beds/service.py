import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.beds.models import Bed, BedPlanting
from app.beds.schemas import BedCreate, BedPlantingCreate, BedPlantingUpdate, BedUpdate


# ─── Beds ─────────────────────────────────────────────────────────

async def get_beds_by_garden(db: AsyncSession, garden_id: int) -> list[Bed]:
    result = await db.execute(
        select(Bed).where(Bed.garden_id == garden_id).order_by(Bed.name)
    )
    return list(result.scalars().all())


async def get_bed_by_id(db: AsyncSession, bed_id: int) -> Bed | None:
    result = await db.execute(select(Bed).where(Bed.id == bed_id))
    return result.scalar_one_or_none()


async def create_bed(db: AsyncSession, data: BedCreate) -> Bed:
    bed_data = data.model_dump()
    # Serialize GeoJSON dict to string for storage
    if bed_data.get("geometry") is not None:
        bed_data["geometry"] = json.dumps(bed_data["geometry"])
    bed = Bed(**bed_data)
    db.add(bed)
    await db.flush()
    await db.refresh(bed)
    return bed


async def update_bed(db: AsyncSession, bed: Bed, data: BedUpdate) -> Bed:
    update_data = data.model_dump(exclude_unset=True)
    if "geometry" in update_data and update_data["geometry"] is not None:
        update_data["geometry"] = json.dumps(update_data["geometry"])
    for field, value in update_data.items():
        setattr(bed, field, value)
    await db.flush()
    await db.refresh(bed)
    return bed


async def delete_bed(db: AsyncSession, bed: Bed) -> None:
    await db.delete(bed)
    await db.flush()


# ─── Bed Plantings ────────────────────────────────────────────────

async def get_plantings_by_bed(db: AsyncSession, bed_id: int) -> list[BedPlanting]:
    result = await db.execute(
        select(BedPlanting).where(BedPlanting.bed_id == bed_id).order_by(BedPlanting.created_at.desc())
    )
    return list(result.scalars().all())


async def get_planting_by_id(db: AsyncSession, planting_id: int) -> BedPlanting | None:
    result = await db.execute(select(BedPlanting).where(BedPlanting.id == planting_id))
    return result.scalar_one_or_none()


async def create_planting(db: AsyncSession, data: BedPlantingCreate) -> BedPlanting:
    planting = BedPlanting(**data.model_dump())
    db.add(planting)
    await db.flush()
    await db.refresh(planting)
    return planting


async def update_planting(
    db: AsyncSession, planting: BedPlanting, data: BedPlantingUpdate
) -> BedPlanting:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(planting, field, value)
    await db.flush()
    await db.refresh(planting)
    return planting


async def delete_planting(db: AsyncSession, planting: BedPlanting) -> None:
    await db.delete(planting)
    await db.flush()

