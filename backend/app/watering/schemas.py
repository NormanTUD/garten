from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Shared summaries ─────────────────────────────────────────────

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str


class BedSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# ─── Watering Event ───────────────────────────────────────────────

class WateringEventCreate(BaseModel):
    bed_id: int | None = None
    started_at: datetime
    duration_minutes: int | None = Field(default=None, ge=0)
    water_amount_liters: float | None = Field(default=None, ge=0)
    method: str = Field(default="manual", pattern=r"^(manual|automatic)$")
    weather_temp_c: float | None = None
    weather_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    weather_rain_mm: float | None = Field(default=None, ge=0)
    weather_description: str | None = Field(default=None, max_length=200)
    soil_moisture_before: float | None = Field(default=None, ge=0, le=100)
    soil_moisture_after: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class WateringEventUpdate(BaseModel):
    bed_id: int | None = None
    started_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    water_amount_liters: float | None = Field(default=None, ge=0)
    method: str | None = Field(default=None, pattern=r"^(manual|automatic)$")
    weather_temp_c: float | None = None
    weather_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    weather_rain_mm: float | None = Field(default=None, ge=0)
    weather_description: str | None = Field(default=None, max_length=200)
    soil_moisture_before: float | None = Field(default=None, ge=0, le=100)
    soil_moisture_after: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class WateringEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user: UserSummary
    bed_id: int | None
    bed: BedSummary | None
    started_at: datetime
    duration_minutes: int | None
    water_amount_liters: float | None
    method: str
    weather_temp_c: float | None
    weather_humidity_pct: float | None
    weather_rain_mm: float | None
    weather_description: str | None
    soil_moisture_before: float | None
    soil_moisture_after: float | None
    notes: str | None
    created_at: datetime


# ─── Fertilizing Event ────────────────────────────────────────────

class FertilizingEventCreate(BaseModel):
    bed_id: int | None = None
    fertilizer_type: str = Field(..., min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, pattern=r"^(kg|g|l|ml|stueck)$")
    date: date
    notes: str | None = None


class FertilizingEventUpdate(BaseModel):
    bed_id: int | None = None
    fertilizer_type: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, pattern=r"^(kg|g|l|ml|stueck)$")
    date: date | None = None
    notes: str | None = None


class FertilizingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user: UserSummary
    bed_id: int | None
    bed: BedSummary | None
    fertilizer_type: str
    amount: float | None
    unit: str | None
    date: date
    notes: str | None
    created_at: datetime

