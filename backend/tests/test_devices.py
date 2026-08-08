"""Tests for the IoT devices module (registration, auth, heartbeat, events)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
async def registered_device(admin_user):
    """Register a new camera device via the admin API. Returns
    ``(device_dict, api_key)``."""
    admin, token = admin_user

    # We need a real AsyncClient, so use the one from conftest via admin_client.
    raise NotImplementedError  # populated per-test via helper


# ─── Registration & API-key auth ──────────────────────────────────


async def test_register_device_returns_api_key_once(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/devices/",
        json={"name": "Pi Cam 1", "device_type": "camera", "location": "Ecke Nord"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pi Cam 1"
    assert data["device_type"] == "camera"
    assert data["is_active"] is True
    assert "api_key" in data
    assert len(data["api_key"]) >= 32


async def test_register_device_requires_admin(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.post(
        "/api/devices/",
        json={"name": "X", "device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_device_auth_with_x_device_key_header(client: AsyncClient, admin_user):
    """The camera pushes with ``X-Device-Key``; the server identifies it."""
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "Auth Cam", "device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = register.json()["api_key"]

    # /api/device/me with the key
    resp = await client.get("/api/device/me", headers={"X-Device-Key": api_key})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Auth Cam"


async def test_device_auth_with_bearer_token(client: AsyncClient, admin_user):
    """Bearer <key> also works."""
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "Bearer Cam", "device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = register.json()["api_key"]

    resp = await client.get("/api/device/me", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 200


async def test_device_auth_rejects_invalid_key(client: AsyncClient):
    resp = await client.get("/api/device/me", headers={"X-Device-Key": "totally-wrong"})
    assert resp.status_code == 401


async def test_device_auth_rejects_missing_key(client: AsyncClient):
    resp = await client.get("/api/device/me")
    assert resp.status_code == 401


async def test_device_auth_rejects_inactive_device(client: AsyncClient, admin_user):
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "Soon Off", "device_type": "sensor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = register.json()["api_key"]
    device_id = register.json()["id"]

    # Deactivate
    await client.patch(
        f"/api/devices/{device_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get("/api/device/me", headers={"X-Device-Key": api_key})
    assert resp.status_code == 403


# ─── Heartbeat & events ───────────────────────────────────────────


async def test_device_heartbeat_updates_last_seen(client: AsyncClient, admin_user):
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "HB Cam", "device_type": "sensor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = register.json()["api_key"]

    resp = await client.post(
        "/api/device/heartbeat",
        json={"status": "ok", "metrics": {"cpu": 12.3, "temp": 41.5}},
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["last_seen_at"] is not None

    # Verify a heartbeat event was logged
    events = await client.get(
        "/api/devices/events/all", params={"event_type": "heartbeat"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    assert len(events.json()) >= 1
    assert events.json()[0]["payload"]["cpu"] == 12.3


async def test_device_post_event(client: AsyncClient, admin_user):
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "Evt Cam", "device_type": "sensor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = register.json()["api_key"]

    resp = await client.post(
        "/api/device/events",
        json={
            "event_type": "motion",
            "severity": "warning",
            "message": "Bewegung erkannt",
            "payload": {"score": 0.92},
        },
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "motion"
    assert data["payload"]["score"] == 0.92


async def test_event_severity_validation(client: AsyncClient, admin_user):
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "Sev Cam", "device_type": "sensor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = register.json()["api_key"]
    resp = await client.post(
        "/api/device/events",
        json={"event_type": "x", "severity": "invalid-level"},
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 422


# ─── Admin: list / update / delete ─────────────────────────────────


async def test_list_devices_admin(client: AsyncClient, admin_user):
    _, token = admin_user
    for n in ("A", "B", "C"):
        await client.post(
            "/api/devices/",
            json={"name": n, "device_type": "sensor"},
            headers={"Authorization": f"Bearer {token}"},
        )
    resp = await client.get("/api/devices/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_list_devices_filter_by_type(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/devices/", json={"name": "C", "device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/devices/", json={"name": "V", "device_type": "valve_controller"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/devices/", params={"device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert all(d["device_type"] == "camera" for d in resp.json())


async def test_delete_device_cascades_events(client: AsyncClient, admin_user):
    _, token = admin_user
    register = await client.post(
        "/api/devices/",
        json={"name": "Doomed", "device_type": "sensor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = register.json()["id"]
    api_key = register.json()["api_key"]
    await client.post(
        "/api/device/events",
        json={"event_type": "ping"},
        headers={"X-Device-Key": api_key},
    )

    await client.delete(
        f"/api/devices/{device_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/devices/{device_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
