"""REST endpoints for cameras, image ingestion, known persons, alerts."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.auth.apikeys.security import Principal, get_current_principal, require_scope
from app.auth.permissions import Scope
from app.cameras import service
from app.cameras.models import Camera, CameraAlert, CapturedImage, KnownPerson
from app.cameras.schemas import (
    CameraAlertCreate,
    CameraAlertRead,
    CameraCreate,
    CameraRead,
    CameraUpdate,
    CapturedImageRead,
    FaceDetectionCreate,
    FaceDetectionRead,
    ImageIngestResponse,
    ImageMetadata,
    KnownPersonCreate,
    KnownPersonRead,
    KnownPersonUpdate,
)
from app.config import settings
from app.dependencies import AdminUser, CurrentUser, DBSession
from app.devices.models import Device
from app.devices.security import get_current_device

logger = logging.getLogger("gartenapp.cameras")

# Cameras – admin CRUD
router = APIRouter(prefix="/api/cameras", tags=["cameras"])
# Device-side image upload endpoint (camera pushes images)
ingest_router = APIRouter(prefix="/api/device/camera", tags=["device-camera"])


# ─── Cameras (admin) ─────────────────────────────────────────────────


@router.post("/", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
async def create_camera(data: CameraCreate, admin: AdminUser, db: DBSession):
    try:
        camera = await service.create_camera(db, data)
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    await db.commit()
    return camera


@router.get("/", response_model=list[CameraRead])
async def list_cameras(
    admin: AdminUser, db: DBSession, active_only: bool = Query(default=False)
):
    return await service.list_cameras(db, active_only=active_only)


@router.get("/{camera_id}", response_model=CameraRead)
async def get_camera(camera_id: int, admin: AdminUser, db: DBSession):
    camera = await service.get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


@router.patch("/{camera_id}", response_model=CameraRead)
async def update_camera(
    camera_id: int, data: CameraUpdate, admin: AdminUser, db: DBSession
):
    camera = await service.get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return await service.update_camera(db, camera, data)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, admin: AdminUser, db: DBSession):
    camera = await service.get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Camera not found")
    await service.delete_camera(db, camera)
    await db.commit()


# ─── Image retrieval (users / admins) ───────────────────────────────


@router.get("/{camera_id}/images", response_model=list[CapturedImageRead])
async def list_camera_images(
    camera_id: int,
    user: CurrentUser,
    db: DBSession,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    camera = await service.get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return await service.list_images(
        db,
        camera_id=camera_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/images/{image_id}", response_model=CapturedImageRead)
async def get_image(image_id: int, user: CurrentUser, db: DBSession):
    image = await service.get_image(db, image_id)
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


@router.get("/images/{image_id}/file")
async def get_image_file(image_id: int, user: CurrentUser, db: DBSession):
    image = await service.get_image(db, image_id)
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    path = settings.upload_dir.parent / image.file_path
    if not path.exists():
        # Already relative to upload_dir? try directly:
        path = Path(image.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image file missing")
    return FileResponse(path, media_type=image.mime_type)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: int, admin: AdminUser, db: DBSession):
    image = await service.get_image(db, image_id)
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    await service.delete_image(db, image)
    await db.commit()


# ─── Known persons (admin) ──────────────────────────────────────────


@router.post("/persons", response_model=KnownPersonRead, status_code=status.HTTP_201_CREATED)
async def create_known_person(data: KnownPersonCreate, admin: AdminUser, db: DBSession):
    person = await service.create_known_person(db, data)
    await db.commit()
    return person


@router.get("/persons", response_model=list[KnownPersonRead])
async def list_known_persons(
    user: CurrentUser, db: DBSession, active_only: bool = Query(default=True)
):
    return await service.list_known_persons(db, active_only=active_only)


@router.get("/persons/{person_id}", response_model=KnownPersonRead)
async def get_known_person(person_id: int, user: CurrentUser, db: DBSession):
    person = await service.get_known_person(db, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.patch("/persons/{person_id}", response_model=KnownPersonRead)
async def update_known_person(
    person_id: int, data: KnownPersonUpdate, admin: AdminUser, db: DBSession
):
    person = await service.get_known_person(db, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Person not found")
    return await service.update_known_person(db, person, data)


@router.delete("/persons/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_known_person(person_id: int, admin: AdminUser, db: DBSession):
    person = await service.get_known_person(db, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Person not found")
    await service.delete_known_person(db, person)
    await db.commit()


# ─── Face detections ────────────────────────────────────────────────


@router.post(
    "/images/{image_id}/faces",
    response_model=FaceDetectionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_face_detection(
    image_id: int,
    data: FaceDetectionCreate,
    admin: AdminUser,
    db: DBSession,
):
    image = await service.get_image(db, image_id)
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    return await service.add_face_detection(db, image, data)


@router.get("/images/{image_id}/faces", response_model=list[FaceDetectionRead])
async def list_face_detections(
    image_id: int,
    user: CurrentUser,
    db: DBSession,
):
    image = await service.get_image(db, image_id)
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    return await service.list_face_detections(db, image_id=image_id)


@router.get("/faces/unknown", response_model=list[FaceDetectionRead])
async def list_unknown_faces(
    user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return await service.list_face_detections(
        db, only_unknown=True, limit=limit, offset=offset
    )


# ─── Alerts ──────────────────────────────────────────────────────────


@router.post(
    "/{camera_id}/alerts",
    response_model=CameraAlertRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera_alert(
    camera_id: int, data: CameraAlertCreate, admin: AdminUser, db: DBSession
):
    camera = await service.get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Camera not found")
    alert = await service.create_alert(db, camera, data)
    await db.commit()
    return alert


@router.get("/alerts/all", response_model=list[CameraAlertRead])
async def list_alerts(
    user: CurrentUser,
    db: DBSession,
    camera_id: int | None = Query(default=None),
    unacknowledged_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return await service.list_alerts(
        db,
        camera_id=camera_id,
        unacknowledged_only=unacknowledged_only,
        limit=limit,
        offset=offset,
    )


@router.post("/alerts/{alert_id}/ack", response_model=CameraAlertRead)
async def acknowledge_camera_alert(
    alert_id: int, user: CurrentUser, db: DBSession
):
    result = await db.execute(
        select(CameraAlert).where(CameraAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return await service.acknowledge_alert(db, alert, user.id)


# ─── Device-side: image ingestion (camera pushes images) ────────────


@ingest_router.post(
    "/image",
    response_model=ImageIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def push_image(
    request: Request,
    device: Annotated[Device, Depends(get_current_device)],
    db: DBSession,
    mime_type: str = Query(default="image/jpeg", max_length=50),
    width: int | None = Query(default=None, ge=1, le=20000),
    height: int | None = Query(default=None, ge=1, le=20000),
    trigger: str = Query(default="manual", max_length=30),
    motion_score: float | None = Query(default=None, ge=0, le=1),
    weather_temp_c: float | None = Query(default=None),
    weather_desc: str | None = Query(default=None, max_length=100),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    notes: str | None = Query(default=None),
    captured_at: datetime | None = Query(default=None),
):
    """Camera (or any device) pushes a captured image here.

    The raw image bytes are sent as the request body, with metadata
    provided as query parameters (simpler than multipart for embedded
    clients). Returns the persisted image plus any alerts that were
    generated automatically.
    """
    camera = await service.get_camera_for_device(db, device)
    if camera is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="No camera registered for this device",
        )

    metadata = ImageMetadata(
        width=width,
        height=height,
        mime_type=mime_type,
        trigger=trigger,
        motion_score=motion_score,
        weather_temp_c=weather_temp_c,
        weather_desc=weather_desc,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
        captured_at=captured_at,
    )

    body = await request.body()
    try:
        image, alerts = await service.ingest_image(db, camera, body, metadata)
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

    await db.commit()
    return ImageIngestResponse(
        image=CapturedImageRead.model_validate(image),
        alerts_created=[a.id for a in alerts],
        faces_detected=0,
    )
