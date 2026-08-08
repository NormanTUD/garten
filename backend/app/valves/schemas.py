"""Pydantic schemas for the valves module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Valves ──────────────────────────────────────────────────────────


class ValveCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    device_id: int | None = None
    bed_id: int | None = None
    hardware_id: str | None = Field(default=None, max_length=100)
    gpio_pin: int | None = Field(default=None, ge=0, le=255)
    normally_open: bool = False
    max_runtime_seconds: int = Field(default=3600, ge=1, le=86400)
    flow_liters_per_minute: float | None = Field(default=None, ge=0, le=1000)
    description: str | None = None


class ValveUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    bed_id: int | None = None
    hardware_id: str | None = Field(default=None, max_length=100)
    gpio_pin: int | None = Field(default=None, ge=0, le=255)
    normally_open: bool | None = None
    max_runtime_seconds: int | None = Field(default=None, ge=1, le=86400)
    flow_liters_per_minute: float | None = Field(default=None, ge=0, le=1000)
    description: str | None = None
    is_active: bool | None = None


class ValveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    device_id: int | None
    bed_id: int | None
    hardware_id: str | None
    gpio_pin: int | None
    normally_open: bool
    max_runtime_seconds: int
    flow_liters_per_minute: float | None
    is_active: bool
    current_state: str
    desired_state: str
    state_changed_at: datetime | None
    created_at: datetime


# ─── Schedules ───────────────────────────────────────────────────────


DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class ScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    start_time: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_seconds: int = Field(..., ge=1, le=86400)
    days_of_week: list[str] = Field(..., min_length=1)
    is_active: bool = True
    notes: str | None = None

    @field_validator("days_of_week")
    @classmethod
    def _validate_days(cls, v: list[str]) -> list[str]:
        normalized = [d.lower() for d in v]
        bad = [d for d in normalized if d not in DAYS]
        if bad:
            raise ValueError(f"Invalid days: {bad}. Allowed: {list(DAYS)}")
        return normalized


class ScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    days_of_week: list[str] | None = None
    is_active: bool | None = None
    notes: str | None = None


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    valve_id: int
    name: str
    start_time: str
    duration_seconds: int
    days_of_week: list[str]
    is_active: bool
    last_run_at: datetime | None
    notes: str | None
    created_at: datetime


# ─── State commands ─────────────────────────────────────────────────


class ValveStateCommand(BaseModel):
    new_state: str = Field(..., pattern=r"^(open|closed)$")
    reason: str | None = Field(default=None, max_length=200)
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)


class ValvePollEntry(BaseModel):
    """One entry in the poll response sent to the controller."""

    valve_id: int
    hardware_id: str | None
    desired_state: str
    duration_seconds: int | None = None
    expected_close_at: datetime | None = None


class ValvePollResponse(BaseModel):
    """Response of GET /api/device/valves/poll – the controller applies
    every entry to its physical valves."""

    server_time: datetime
    entries: list[ValvePollEntry]


class ValveStateReport(BaseModel):
    """POSTed by the controller when it has actually changed a valve."""

    valve_id: int
    current_state: str = Field(..., pattern=r"^(open|closed|error)$")
    water_amount_liters: float | None = Field(default=None, ge=0)
    error_message: str | None = None


# ─── Events ──────────────────────────────────────────────────────────


class ValveEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    valve_id: int
    new_state: str
    triggered_by: str
    triggered_by_id: int | None
    reason: str | None
    opened_at: datetime
    closed_at: datetime | None
    water_amount_liters: float | None
