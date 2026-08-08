"""Pydantic schemas for IoT device endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegister(BaseModel):
    """Admin-issued device registration payload."""

    name: str = Field(..., min_length=1, max_length=100)
    device_type: str = Field(
        ..., min_length=1, max_length=50,
        description="e.g. camera, valve_controller, sensor",
    )
    hardware_id: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = None


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    device_type: str
    hardware_id: str | None
    location: str | None
    description: str | None
    is_active: bool
    last_seen_at: datetime | None
    registered_at: datetime


class DeviceCreated(DeviceRead):
    """Response of POST /devices/ – includes the freshly minted API key.

    The key is returned **once**; the server only stores its hash.
    """

    api_key: str


class DeviceEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    severity: str = Field(default="info", pattern=r"^(info|warning|error|critical)$")
    payload: dict | None = None
    message: str | None = None
    occurred_at: datetime | None = None


class DeviceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    event_type: str
    severity: str
    payload: dict | None
    message: str | None
    occurred_at: datetime
    received_at: datetime


class DeviceHeartbeat(BaseModel):
    status: str = Field(default="ok", pattern=r"^(ok|degraded|error)$")
    metrics: dict | None = None
