"""Camera devices + captured images + alerts + face recognition hooks."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Camera(Base):
    """A camera device with capture configuration."""

    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stream_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snapshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Auto-capture interval (seconds). 0 = motion only.
    capture_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    # How long to keep images on disk before auto-purge.
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    detect_faces: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="camera")  # noqa: F821
    images: Mapped[list[CapturedImage]] = relationship(
        back_populates="camera",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CapturedImage(Base):
    """An image captured by a camera, with metadata."""

    __tablename__ = "captured_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="image/jpeg")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    trigger: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    motion_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_desc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    camera: Mapped[Camera] = relationship(back_populates="images")
    faces: Mapped[list[FaceDetection]] = relationship(
        back_populates="image",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alerts: Mapped[list[CameraAlert]] = relationship(
        back_populates="image",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnownPerson(Base):
    """A person known to the system (face embeddings + optional MAC)."""

    __tablename__ = "known_persons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # List of base64-encoded embeddings (opaque to the server – the face
    # recognition service is pluggable). Stored as JSON list[str].
    face_embeddings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    detections: Mapped[list[FaceDetection]] = relationship(
        back_populates="person", lazy="selectin"
    )


class FaceDetection(Base):
    """A single face detected within a captured image."""

    __tablename__ = "face_detections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("captured_images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("known_persons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_unknown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    image: Mapped[CapturedImage] = relationship(back_populates="faces")
    person: Mapped[KnownPerson | None] = relationship(back_populates="detections")


class CameraAlert(Base):
    """Alert triggered by a camera (unknown face, motion at unusual time, …)."""

    __tablename__ = "camera_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("captured_images.id", ondelete="SET NULL"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    acknowledged_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    camera: Mapped[Camera] = relationship()
    image: Mapped[CapturedImage | None] = relationship(back_populates="alerts")
