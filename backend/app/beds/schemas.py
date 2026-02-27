from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Bed ──────────────────────────────────────────────────────────

class BedCreate(BaseModel):
    garden_id: int
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    geometry: dict | None = None
    area_sqm: float | None = Field(default=None, ge=0)
    soil_type: str | None = Field(default=None, max_length=50)
    sun_exposure: str | None = Field(default=None, pattern=r"^(full_sun|partial_shade|full_shade)$")


class BedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    geometry: dict | None = None
    area_sqm: float | None = Field(default=None, ge=0)
    soil_type: str | None = Field(default=None, max_length=50)
    sun_exposure: str | None = Field(default=None, pattern=r"^(full_sun|partial_shade|full_shade)$")


class BedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    garden_id: int
    name: str
    description: str | None
    geometry: dict | None
    area_sqm: float | None
    soil_type: str | None
    sun_exposure: str | None
    created_at: datetime


# ─── BedPlanting ──────────────────────────────────────────────────

class BedPlantingCreate(BaseModel):
    bed_id: int
    plant_id: int
    planted_at: date | None = None
    expected_harvest_date: date | None = None
    status: str = Field(default="active", pattern=r"^(active|harvested|removed)$")
    notes: str | None = None


class BedPlantingUpdate(BaseModel):
    planted_at: date | None = None
    expected_harvest_date: date | None = None
    status: str | None = Field(default=None, pattern=r"^(active|harvested|removed)$")
    notes: str | None = None


class PlantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    variety: str | None


class BedPlantingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bed_id: int
    plant_id: int
    plant: PlantSummary
    planted_at: date | None
    expected_harvest_date: date | None
    status: str
    notes: str | None
    created_at: datetime

