"""Pydantic schemas for the cameras module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.network.models import normalize_mac

# ─── Camera ──────────────────────────────────────────────────────────


class CameraCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    stream_url: str | None = Field(default=None, max_length=500)
    snapshot_url: str | None = Field(default=None, max_length=500)
    capture_interval_seconds: int = Field(default=300, ge=0, le=86400)
    retention_days: int = Field(default=90, ge=1, le=3650)
    detect_faces: bool = True


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    stream_url: str | None = Field(default=None, max_length=500)
    snapshot_url: str | None = Field(default=None, max_length=500)
    capture_interval_seconds: int | None = Field(default=None, ge=0, le=86400)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    detect_faces: bool | None = None
    is_active: bool | None = None


class CameraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    name: str
    location: str | None
    stream_url: str | None
    snapshot_url: str | None
    capture_interval_seconds: int
    retention_days: int
    detect_faces: bool
    is_active: bool
    created_at: datetime


# ─── Image ingestion (device-side) ──────────────────────────────────


class ImageMetadata(BaseModel):
    width: int | None = Field(default=None, ge=1, le=20000)
    height: int | None = Field(default=None, ge=1, le=20000)
    mime_type: str = Field(default="image/jpeg", max_length=50)
    trigger: str = Field(default="manual", max_length=30)
    motion_score: float | None = Field(default=None, ge=0, le=1)
    weather_temp_c: float | None = None
    weather_desc: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = None
    captured_at: datetime | None = None
    extra: dict | None = None


class CapturedImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    file_path: str
    thumbnail_path: str | None
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    captured_at: datetime
    received_at: datetime
    trigger: str
    motion_score: float | None
    weather_temp_c: float | None
    weather_desc: str | None
    latitude: float | None
    longitude: float | None
    notes: str | None


class ImageIngestResponse(BaseModel):
    image: CapturedImageRead
    alerts_created: list[int]
    faces_detected: int


# ─── Known persons ───────────────────────────────────────────────────


class KnownPersonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    user_id: int | None = None
    mac_address: str | None = Field(
        default=None, max_length=17, description="e.g. AA:BB:CC:DD:EE:FF"
    )
    notes: str | None = None
    face_embeddings: list[str] | None = None

    @field_validator("mac_address")
    @classmethod
    def _normalize_mac(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return normalize_mac(v)
        except ValueError as err:
            raise ValueError(str(err)) from err


class KnownPersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: int | None = None
    mac_address: str | None = Field(default=None, max_length=17)
    notes: str | None = None
    face_embeddings: list[str] | None = None
    is_active: bool | None = None

    @field_validator("mac_address")
    @classmethod
    def _normalize_mac(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return normalize_mac(v)
        except ValueError as err:
            raise ValueError(str(err)) from err


class KnownPersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    user_id: int | None
    mac_address: str | None
    notes: str | None
    is_active: bool
    created_at: datetime


# ─── Face detections ─────────────────────────────────────────────────


class FaceDetectionCreate(BaseModel):
    bounding_box: dict | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    person_id: int | None = None
    is_unknown: bool = False
    embedding: str | None = None


class FaceDetectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_id: int
    person_id: int | None
    bounding_box: dict | None
    confidence: float
    is_unknown: bool
    detected_at: datetime


# ─── Alerts ──────────────────────────────────────────────────────────


class CameraAlertCreate(BaseModel):
    alert_type: str = Field(..., min_length=1, max_length=50)
    severity: str = Field(default="warning", pattern=r"^(info|warning|error|critical)$")
    message: str = Field(..., min_length=1, max_length=500)
    image_id: int | None = None


class CameraAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    image_id: int | None
    alert_type: str
    severity: str
    message: str
    acknowledged_by_id: int | None
    acknowledged_at: datetime | None
    created_at: datetime
