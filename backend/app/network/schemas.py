"""Pydantic schemas for the network allowlist."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.network.models import normalize_mac


class NetworkDeviceCreate(BaseModel):
    mac_address: str = Field(..., min_length=11, max_length=17)
    name: str = Field(..., min_length=1, max_length=100)
    device_type: str = Field(
        default="unknown",
        pattern=r"^(camera|valve|sensor|phone|laptop|tablet|unknown)$",
    )
    owner_user_id: int | None = None
    known_person_id: int | None = None
    notes: str | None = None
    is_trusted: bool = True

    @field_validator("mac_address")
    @classmethod
    def _normalize_mac(cls, v: str) -> str:
        try:
            return normalize_mac(v)
        except ValueError as err:
            raise ValueError(str(err)) from err


class NetworkDeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    device_type: str | None = Field(
        default=None, pattern=r"^(camera|valve|sensor|phone|laptop|tablet|unknown)$"
    )
    owner_user_id: int | None = None
    known_person_id: int | None = None
    notes: str | None = None
    is_trusted: bool | None = None
    is_active: bool | None = None


class NetworkDeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mac_address: str
    name: str
    device_type: str
    owner_user_id: int | None
    known_person_id: int | None
    notes: str | None
    is_trusted: bool
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime


class MacLookupResponse(BaseModel):
    """Result of a MAC-allowlist lookup. Returns whether the MAC is trusted."""

    mac_address: str
    is_trusted: bool
    is_active: bool
    device_name: str | None
    owner_user_id: int | None
    known_person_id: int | None
