from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GardenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    total_area_sqm: float | None = Field(default=None, ge=0)


class GardenUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    total_area_sqm: float | None = Field(default=None, ge=0)


class GardenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    location_lat: float | None
    location_lng: float | None
    total_area_sqm: float | None
    created_at: datetime

