from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    variety: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    icon: str | None = Field(default=None, max_length=50)
    expected_water_needs: str | None = Field(
        default=None, pattern=r"^(low|medium|high)$"
    )
    growing_season_start: int | None = Field(default=None, ge=1, le=12)
    growing_season_end: int | None = Field(default=None, ge=1, le=12)
    notes: str | None = None


class PlantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    variety: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    icon: str | None = Field(default=None, max_length=50)
    expected_water_needs: str | None = Field(
        default=None, pattern=r"^(low|medium|high)$"
    )
    growing_season_start: int | None = Field(default=None, ge=1, le=12)
    growing_season_end: int | None = Field(default=None, ge=1, le=12)
    notes: str | None = None


class PlantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    variety: str | None
    category: str | None
    icon: str | None
    expected_water_needs: str | None
    growing_season_start: int | None
    growing_season_end: int | None
    notes: str | None
    created_at: datetime

