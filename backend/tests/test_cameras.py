"""Tests for the cameras module: CRUD, image ingestion, alerts, faces, persons."""
from __future__ import annotations

from httpx import AsyncClient

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 32


async def _create_camera_device(client: AsyncClient, token: str, name: str = "Pi Cam") -> tuple[int, str]:
    register = await client.post(
        "/api/devices/",
        json={"name": name, "device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert register.status_code == 201, register.text
    device_id = register.json()["id"]
    api_key = register.json()["api_key"]

    cam = await client.post(
        "/api/cameras/",
        json={
            "device_id": device_id,
            "name": name,
            "location": "Haupteingang",
            "capture_interval_seconds": 60,
            "retention_days": 7,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cam.status_code == 201, cam.text
    return cam.json()["id"], api_key


# ─── Camera CRUD ────────────────────────────────────────────────────


async def test_create_camera_requires_device_type_camera(client: AsyncClient, admin_user):
    _, token = admin_user
    reg = await client.post(
        "/api/devices/", json={"name": "Wrong Type", "device_type": "valve_controller"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = reg.json()["id"]
    resp = await client.post(
        "/api/cameras/",
        json={"device_id": device_id, "name": "Should fail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "camera" in resp.json()["detail"].lower()


async def test_create_camera_requires_existing_device(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/cameras/",
        json={"device_id": 9999, "name": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_device_can_only_have_one_camera(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, _ = await _create_camera_device(client, token)
    # Get the device_id from the existing camera
    cameras = await client.get("/api/cameras/", headers={"Authorization": f"Bearer {token}"})
    device_id = cameras.json()[0]["device_id"]
    resp = await client.post(
        "/api/cameras/",
        json={"device_id": device_id, "name": "dup"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


async def test_list_cameras(client: AsyncClient, admin_user):
    _, token = admin_user
    await _create_camera_device(client, token, name="A")
    await _create_camera_device(client, token, name="B")
    resp = await client.get("/api/cameras/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_update_and_delete_camera(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, _ = await _create_camera_device(client, token)
    resp = await client.patch(
        f"/api/cameras/{cam_id}",
        json={"retention_days": 30, "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["retention_days"] == 30
    assert resp.json()["is_active"] is False

    delete = await client.delete(
        f"/api/cameras/{cam_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert delete.status_code == 204


# ─── Image ingestion ────────────────────────────────────────────────


async def test_device_pushes_image(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, api_key = await _create_camera_device(client, token)

    # The camera (device) pushes the image; metadata as query params
    resp = await client.post(
        "/api/device/camera/image"
        "?mime_type=image/jpeg"
        "&width=1920"
        "&height=1080"
        "&trigger=motion"
        "&motion_score=0.7",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["image"]["size_bytes"] == len(JPEG_BYTES)
    assert data["image"]["width"] == 1920
    assert data["image"]["trigger"] == "motion"
    assert data["image"]["camera_id"] == cam_id


async def test_image_push_requires_camera_attached(client: AsyncClient, admin_user):
    """A device without a camera can't push images."""
    _, token = admin_user
    reg = await client.post(
        "/api/devices/", json={"name": "NoCam", "device_type": "sensor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = reg.json()["api_key"]

    resp = await client.post(
        "/api/device/camera/image?mime_type=image/jpeg",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 400


async def test_image_push_rejects_unknown_mime(client: AsyncClient, admin_user):
    _, token = admin_user
    _, api_key = await _create_camera_device(client, token)
    resp = await client.post(
        "/api/device/camera/image?mime_type=application/x-binary",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 400


async def test_image_push_rejects_huge_payload(client: AsyncClient, admin_user, monkeypatch):
    _, token = admin_user
    _, api_key = await _create_camera_device(client, token)
    # Make the limit artificially small to test the guard
    from app.cameras import service as svc
    monkeypatch.setattr(svc, "MAX_IMAGE_BYTES", 100)

    resp = await client.post(
        "/api/device/camera/image?mime_type=image/jpeg",
        content=b"\xff" * 1000,
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


async def test_list_camera_images(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, api_key = await _create_camera_device(client, token)
    for _ in range(3):
        await client.post(
            "/api/device/camera/image?mime_type=image/jpeg",
            content=JPEG_BYTES,
            headers={"X-Device-Key": api_key},
        )
    resp = await client.get(
        f"/api/cameras/{cam_id}/images",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ─── Known persons & face detections ───────────────────────────────


async def test_create_known_person_with_mac(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/cameras/persons",
        json={
            "name": "Maria Müller",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "face_embeddings": ["embedding-base64-1", "embedding-base64-2"],
            "notes": "Wohnung 3",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Maria Müller"


async def test_mac_address_normalized(client: AsyncClient, admin_user):
    """``aa-bb-CC-DD-ee-ff`` must be persisted as ``AA:BB:CC:DD:EE:FF``."""
    _, token = admin_user
    resp = await client.post(
        "/api/cameras/persons",
        json={"name": "Hans", "mac_address": "aa-bb-CC-DD-ee-ff"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    # Look up via raw MAC
    lookup = await client.get(
        "/api/network/lookup", params={"mac": "AA:BB:CC:DD:EE:FF"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert lookup.status_code == 200


async def test_invalid_mac_address_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/cameras/persons",
        json={"name": "X", "mac_address": "not-a-mac"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_add_face_detection_unknown_creates_alert(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, api_key = await _create_camera_device(client, token)

    img_resp = await client.post(
        "/api/device/camera/image?mime_type=image/jpeg",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    image_id = img_resp.json()["image"]["id"]

    detection = await client.post(
        f"/api/cameras/images/{image_id}/faces",
        json={"is_unknown": True, "confidence": 0.93, "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detection.status_code == 201
    assert detection.json()["is_unknown"] is True

    alerts = await client.get(
        "/api/cameras/alerts/all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert any(a["alert_type"] == "unknown_person" for a in alerts.json())


async def test_add_known_face_no_alert(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, api_key = await _create_camera_device(client, token)
    img = await client.post(
        "/api/device/camera/image?mime_type=image/jpeg",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    image_id = img.json()["image"]["id"]

    person = await client.post(
        "/api/cameras/persons",
        json={"name": "Known"},
        headers={"Authorization": f"Bearer {token}"},
    )
    det = await client.post(
        f"/api/cameras/images/{image_id}/faces",
        json={"person_id": person.json()["id"], "is_unknown": False, "confidence": 0.95},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert det.status_code == 201

    alerts = await client.get(
        "/api/cameras/alerts/all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert alerts.json() == []


async def test_acknowledge_alert(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, api_key = await _create_camera_device(client, token)
    img = await client.post(
        "/api/device/camera/image?mime_type=image/jpeg",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    image_id = img.json()["image"]["id"]
    await client.post(
        f"/api/cameras/images/{image_id}/faces",
        json={"is_unknown": True, "confidence": 0.8},
        headers={"Authorization": f"Bearer {token}"},
    )
    alerts = await client.get(
        "/api/cameras/alerts/all", headers={"Authorization": f"Bearer {token}"}
    )
    alert_id = alerts.json()[0]["id"]
    assert alerts.json()[0]["acknowledged_at"] is None

    ack = await client.post(
        f"/api/cameras/alerts/{alert_id}/ack",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ack.status_code == 200
    assert ack.json()["acknowledged_at"] is not None


async def test_delete_image(client: AsyncClient, admin_user):
    _, token = admin_user
    cam_id, api_key = await _create_camera_device(client, token)
    img = await client.post(
        "/api/device/camera/image?mime_type=image/jpeg",
        content=JPEG_BYTES,
        headers={"X-Device-Key": api_key},
    )
    image_id = img.json()["image"]["id"]
    delete = await client.delete(
        f"/api/cameras/images/{image_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204
    resp = await client.get(
        f"/api/cameras/images/{image_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
