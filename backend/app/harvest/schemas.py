from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HarvestCreate(BaseModel):
    bed_id: int | None = None
    plant_id: int | None = None
    amount: float = Field(..., gt=0)
    unit: str = Field(..., pattern=r"^(kg|g|stueck|bund|liter|eimer)$")
    quality_rating: int | None = Field(default=None, ge=1, le=5)
    harvest_date: date
    notes: str | None = None


class HarvestUpdate(BaseModel):
    bed_id: int | None = None
    plant_id: int | None = None
    amount: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, pattern=r"^(kg|g|stueck|bund|liter|eimer)$")
    quality_rating: int | None = Field(default=None, ge=1, le=5)
    harvest_date: date | None = None
    notes: str | None = None


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str


class BedSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class PlantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    variety: str | None


class HarvestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user: UserSummary
    bed_id: int | None
    bed: BedSummary | None
    plant_id: int | None
    plant: PlantSummary | None
    amount: float
    unit: str
    quality_rating: int | None
    harvest_date: date
    notes: str | None
    created_at: datetime

