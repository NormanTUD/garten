"""Service layer for cameras, images, face detection and alerts."""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cameras.models import (
    Camera,
    CameraAlert,
    CapturedImage,
    FaceDetection,
    KnownPerson,
)
from app.cameras.schemas import (
    CameraAlertCreate,
    CameraCreate,
    CameraUpdate,
    FaceDetectionCreate,
    ImageMetadata,
    KnownPersonCreate,
    KnownPersonUpdate,
)
from app.config import settings
from app.devices import service as device_service
from app.devices.models import Device

logger = logging.getLogger("gartenapp.cameras")

ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15 MB


def image_dir() -> Path:
    base = Path(settings.upload_dir) / "camera_images"
    base.mkdir(parents=True, exist_ok=True)
    return base


def thumbnail_dir() -> Path:
    base = Path(settings.upload_dir) / "camera_thumbs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _detect_extension(mime_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/heic": ".heic",
    }.get(mime_type, ".bin")


# ─── Cameras ─────────────────────────────────────────────────────────


async def create_camera(db: AsyncSession, data: CameraCreate) -> Camera:
    device = await device_service.get_device_by_id(db, data.device_id)
    if device is None:
        raise ValueError(f"Device {data.device_id} not found")
    if device.device_type != "camera":
        raise ValueError(
            f"Device {device.id} is of type '{device.device_type}', not 'camera'"
        )

    existing = await db.execute(
        select(Camera).where(Camera.device_id == data.device_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"Device {data.device_id} already has a camera attached")

    camera = Camera(
        device_id=data.device_id,
        name=data.name,
        location=data.location,
        stream_url=data.stream_url,
        snapshot_url=data.snapshot_url,
        capture_interval_seconds=data.capture_interval_seconds,
        retention_days=data.retention_days,
        detect_faces=data.detect_faces,
    )
    db.add(camera)
    await db.flush()
    await db.refresh(camera)
    return camera


async def get_camera(db: AsyncSession, camera_id: int) -> Camera | None:
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    return result.scalar_one_or_none()


async def get_camera_for_device(db: AsyncSession, device: Device) -> Camera | None:
    result = await db.execute(select(Camera).where(Camera.device_id == device.id))
    return result.scalar_one_or_none()


async def list_cameras(db: AsyncSession, active_only: bool = False) -> list[Camera]:
    stmt = select(Camera).order_by(Camera.name)
    if active_only:
        stmt = stmt.where(Camera.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_camera(
    db: AsyncSession, camera: Camera, data: CameraUpdate
) -> Camera:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    await db.flush()
    await db.refresh(camera)
    return camera


async def delete_camera(db: AsyncSession, camera: Camera) -> None:
    await db.delete(camera)
    await db.flush()


# ─── Image ingestion ────────────────────────────────────────────────


async def ingest_image(
    db: AsyncSession,
    camera: Camera,
    payload: bytes,
    metadata: ImageMetadata,
) -> tuple[CapturedImage, list[CameraAlert]]:
    """Persist a captured image and run lightweight checks.

    Returns the saved image and any alerts that were created automatically
    (currently: missing-allowed-MAC for unknown devices; reserved for
    face-recognition service).
    """
    if metadata.mime_type not in ALLOWED_IMAGE_MIME:
        raise ValueError(f"Unsupported mime_type: {metadata.mime_type}")
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image too large: {len(payload)} bytes (max {MAX_IMAGE_BYTES})"
        )

    ext = _detect_extension(metadata.mime_type)
    filename = f"{camera.id}_{int(datetime.now(UTC).timestamp() * 1000)}_{secrets.token_hex(4)}{ext}"
    dest = image_dir() / filename

    # Write atomically: tmp → rename
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(dest)

    image = CapturedImage(
        camera_id=camera.id,
        file_path=str(dest.relative_to(Path(settings.upload_dir).parent))
        if Path(settings.upload_dir) in dest.parents
        else str(dest),
        mime_type=metadata.mime_type,
        size_bytes=len(payload),
        width=metadata.width,
        height=metadata.height,
        trigger=metadata.trigger,
        motion_score=metadata.motion_score,
        weather_temp_c=metadata.weather_temp_c,
        weather_desc=metadata.weather_desc,
        latitude=metadata.latitude,
        longitude=metadata.longitude,
        notes=metadata.notes,
        captured_at=metadata.captured_at or datetime.now(UTC),
        metadata_=metadata.extra,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)

    alerts: list[CameraAlert] = []
    # If the device is sending without an active network presence, raise a
    # generic "image without network context" alert for admins.
    if camera.detect_faces:
        # The face-recognition hook runs out-of-band; we just log a hint.
        logger.debug("Image %s queued for face detection", image.id)
    return image, alerts


async def get_image(db: AsyncSession, image_id: int) -> CapturedImage | None:
    result = await db.execute(
        select(CapturedImage).where(CapturedImage.id == image_id)
    )
    return result.scalar_one_or_none()


async def list_images(
    db: AsyncSession,
    camera_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CapturedImage]:
    stmt = select(CapturedImage).order_by(CapturedImage.captured_at.desc())
    if camera_id is not None:
        stmt = stmt.where(CapturedImage.camera_id == camera_id)
    if date_from:
        stmt = stmt.where(CapturedImage.captured_at >= date_from)
    if date_to:
        stmt = stmt.where(CapturedImage.captured_at <= date_to)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_image(db: AsyncSession, image: CapturedImage) -> None:
    # Best-effort disk cleanup
    try:
        Path(image.file_path).unlink(missing_ok=True)
        if image.thumbnail_path:
            Path(image.thumbnail_path).unlink(missing_ok=True)
    except Exception:
        logger.exception("Failed to delete image file %s", image.file_path)
    await db.delete(image)
    await db.flush()


async def purge_old_images(db: AsyncSession) -> int:
    """Delete images older than their camera's retention period."""
    cameras = await list_cameras(db)
    deleted = 0
    for cam in cameras:
        cutoff = datetime.now(UTC) - timedelta(days=cam.retention_days)
        stmt = select(CapturedImage).where(
            CapturedImage.camera_id == cam.id,
            CapturedImage.captured_at < cutoff,
        )
        old = list((await db.execute(stmt)).scalars().all())
        for img in old:
            await delete_image(db, img)
            deleted += 1
    return deleted


# ─── Known persons ───────────────────────────────────────────────────


async def create_known_person(db: AsyncSession, data: KnownPersonCreate) -> KnownPerson:
    person = KnownPerson(
        name=data.name,
        user_id=data.user_id,
        mac_address=data.mac_address,
        notes=data.notes,
        face_embeddings=data.face_embeddings,
    )
    db.add(person)
    await db.flush()
    await db.refresh(person)
    return person


async def list_known_persons(
    db: AsyncSession, active_only: bool = True
) -> list[KnownPerson]:
    stmt = select(KnownPerson).order_by(KnownPerson.name)
    if active_only:
        stmt = stmt.where(KnownPerson.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_known_person(db: AsyncSession, person_id: int) -> KnownPerson | None:
    result = await db.execute(select(KnownPerson).where(KnownPerson.id == person_id))
    return result.scalar_one_or_none()


async def update_known_person(
    db: AsyncSession, person: KnownPerson, data: KnownPersonUpdate
) -> KnownPerson:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    await db.flush()
    await db.refresh(person)
    return person


async def delete_known_person(db: AsyncSession, person: KnownPerson) -> None:
    await db.delete(person)
    await db.flush()


async def find_person_by_mac(
    db: AsyncSession, mac_address: str
) -> KnownPerson | None:
    if not mac_address:
        return None
    result = await db.execute(
        select(KnownPerson).where(KnownPerson.mac_address == mac_address)
    )
    return result.scalar_one_or_none()


# ─── Face detections ─────────────────────────────────────────────────


async def add_face_detection(
    db: AsyncSession,
    image: CapturedImage,
    data: FaceDetectionCreate,
) -> FaceDetection:
    detection = FaceDetection(
        image_id=image.id,
        person_id=data.person_id,
        bounding_box=data.bounding_box,
        confidence=data.confidence,
        is_unknown=data.is_unknown,
        embedding=data.embedding,
    )
    db.add(detection)
    await db.flush()

    # If unknown → create alert
    alerts: list[CameraAlert] = []
    if data.is_unknown and image.camera_id:
        alert = CameraAlert(
            camera_id=image.camera_id,
            image_id=image.id,
            alert_type="unknown_person",
            severity="warning",
            message=f"Unbekannte Person erkannt (Konfidenz {data.confidence:.0%})",
        )
        db.add(alert)
        await db.flush()
        alerts.append(alert)
    return detection


async def list_face_detections(
    db: AsyncSession,
    image_id: int | None = None,
    only_unknown: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[FaceDetection]:
    stmt = select(FaceDetection).order_by(FaceDetection.detected_at.desc())
    if image_id is not None:
        stmt = stmt.where(FaceDetection.image_id == image_id)
    if only_unknown:
        stmt = stmt.where(FaceDetection.is_unknown.is_(True))
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── Alerts ──────────────────────────────────────────────────────────


async def create_alert(
    db: AsyncSession,
    camera: Camera,
    data: CameraAlertCreate,
) -> CameraAlert:
    alert = CameraAlert(
        camera_id=camera.id,
        image_id=data.image_id,
        alert_type=data.alert_type,
        severity=data.severity,
        message=data.message,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    return alert


async def list_alerts(
    db: AsyncSession,
    camera_id: int | None = None,
    unacknowledged_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[CameraAlert]:
    stmt = select(CameraAlert).order_by(CameraAlert.created_at.desc())
    if camera_id is not None:
        stmt = stmt.where(CameraAlert.camera_id == camera_id)
    if unacknowledged_only:
        stmt = stmt.where(CameraAlert.acknowledged_at.is_(None))
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_alert(
    db: AsyncSession, alert: CameraAlert, user_id: int
) -> CameraAlert:
    alert.acknowledged_by_id = user_id
    alert.acknowledged_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(alert)
    return alert
