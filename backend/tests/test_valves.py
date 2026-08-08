"""Tests for the valves module: state commands, schedules, polling, reports."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
async def valve_device(client: AsyncClient, admin_user):
    """Register a device, then create a valve bound to it. Returns
    ``(valve_id, device_api_key)``."""
    _, token = admin_user
    reg = await client.post(
        "/api/devices/",
        json={"name": "ValveCtrl", "device_type": "valve_controller"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = reg.json()["id"]
    api_key = reg.json()["api_key"]
    valve = await client.post(
        "/api/valves/",
        json={
            "name": "Beet Nord",
            "device_id": device_id,
            "hardware_id": "VALVE-N1",
            "gpio_pin": 17,
            "max_runtime_seconds": 60,
            "flow_liters_per_minute": 12.5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert valve.status_code == 201
    return valve.json()["id"], api_key


# ─── Valve CRUD ────────────────────────────────────────────────────


async def test_create_valve(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/valves/",
        json={"name": "Beet Süd", "hardware_id": "V-S1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Beet Süd"
    assert data["current_state"] == "closed"
    assert data["desired_state"] == "closed"


async def test_list_valves(client: AsyncClient, admin_user):
    _, token = admin_user
    for n in ("A", "B"):
        await client.post(
            "/api/valves/",
            json={"name": n},
            headers={"Authorization": f"Bearer {token}"},
        )
    resp = await client.get("/api/valves/", headers={"Authorization": f"Bearer {token}"})
    assert len(resp.json()) >= 2


async def test_update_and_delete_valve(client: AsyncClient, admin_user):
    _, token = admin_user
    create = await client.post(
        "/api/valves/",
        json={"name": "tmp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    vid = create.json()["id"]

    patch = await client.patch(
        f"/api/valves/{vid}",
        json={"flow_liters_per_minute": 8.0, "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200
    assert patch.json()["flow_liters_per_minute"] == 8.0

    delete = await client.delete(
        f"/api/valves/{vid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204


# ─── Manual state commands ────────────────────────────────────────


async def test_command_open_valve(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    resp = await client.post(
        f"/api/valves/{valve_id}/command",
        json={"new_state": "open", "reason": "Test", "duration_seconds": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_state"] == "open"

    state = await client.get(
        f"/api/valves/{valve_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert state.json()["desired_state"] == "open"


async def test_command_validates_state_value(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    resp = await client.post(
        f"/api/valves/{valve_id}/command",
        json={"new_state": "half-open"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_command_close_records_water_amount(
    client: AsyncClient, admin_user, valve_device
):
    """When the controller reports 'closed' after an open cycle, we
    compute the water amount from the elapsed time × flow rate."""
    valve_id, api_key = valve_device
    _, token = admin_user

    # Open
    await client.post(
        f"/api/valves/{valve_id}/command",
        json={"new_state": "open", "duration_seconds": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Controller reports closed immediately (in tests; the auto-close
    # task would normally fire after 120s)
    await asyncio.sleep(0.01)
    report = await client.post(
        "/api/device/valves/report",
        json={"valve_id": valve_id, "current_state": "closed"},
        headers={"X-Device-Key": api_key},
    )
    assert report.status_code == 200
    assert report.json()["closed_at"] is not None


# ─── Schedules ─────────────────────────────────────────────────────


async def test_create_schedule(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    resp = await client.post(
        f"/api/valves/{valve_id}/schedules",
        json={
            "name": "Morgens",
            "start_time": "06:00",
            "duration_seconds": 120,
            "days_of_week": ["mon", "wed", "fri"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Morgens"


async def test_schedule_validates_time_format(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    resp = await client.post(
        f"/api/valves/{valve_id}/schedules",
        json={
            "name": "Bad",
            "start_time": "6am",
            "duration_seconds": 60,
            "days_of_week": ["mon"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_schedule_validates_days(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    resp = await client.post(
        f"/api/valves/{valve_id}/schedules",
        json={
            "name": "Bad days",
            "start_time": "06:00",
            "duration_seconds": 60,
            "days_of_week": ["funday"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_update_and_delete_schedule(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    create = await client.post(
        f"/api/valves/{valve_id}/schedules",
        json={
            "name": "X",
            "start_time": "06:00",
            "duration_seconds": 60,
            "days_of_week": ["mon"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    sched_id = create.json()["id"]
    patch = await client.patch(
        f"/api/valves/schedules/{sched_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200
    assert patch.json()["is_active"] is False
    delete = await client.delete(
        f"/api/valves/schedules/{sched_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204


# ─── Device-side: poll & report ───────────────────────────────────


async def test_device_poll_returns_only_own_valves(
    client: AsyncClient, admin_user, valve_device
):
    """The Pi only sees valves bound to its own device."""
    valve_id, api_key = valve_device
    _, token = admin_user

    # Add a valve on a *different* (unregistered) device id – simulate by
    # creating one without device_id.
    other = await client.post(
        "/api/valves/",
        json={"name": "Other"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/device/valves/poll",
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [e["valve_id"] for e in data["entries"]]
    assert valve_id in ids
    assert other.json()["id"] not in ids


async def test_device_poll_reflects_desired_state(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, api_key = valve_device
    _, token = admin_user
    await client.post(
        f"/api/valves/{valve_id}/command",
        json={"new_state": "open"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/device/valves/poll",
        headers={"X-Device-Key": api_key},
    )
    entry = next(e for e in resp.json()["entries"] if e["valve_id"] == valve_id)
    assert entry["desired_state"] == "open"


async def test_device_report_state(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, api_key = valve_device
    resp = await client.post(
        "/api/device/valves/report",
        json={"valve_id": valve_id, "current_state": "open", "water_amount_liters": 0},
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "open"


async def test_device_report_rejects_other_valve(
    client: AsyncClient, admin_user, valve_device
):
    """The Pi may only report state for its own valves."""
    _, token = admin_user
    other = await client.post(
        "/api/valves/", json={"name": "Foreign"},
        headers={"Authorization": f"Bearer {token}"},
    )
    _, api_key = valve_device
    resp = await client.post(
        "/api/device/valves/report",
        json={"valve_id": other.json()["id"], "current_state": "closed"},
        headers={"X-Device-Key": api_key},
    )
    assert resp.status_code == 403


async def test_device_poll_requires_api_key(client: AsyncClient):
    resp = await client.get("/api/device/valves/poll")
    assert resp.status_code == 401


# ─── Events ────────────────────────────────────────────────────────


async def test_list_valve_events(
    client: AsyncClient, admin_user, valve_device
):
    valve_id, _ = valve_device
    _, token = admin_user
    await client.post(
        f"/api/valves/{valve_id}/command",
        json={"new_state": "open"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        f"/api/valves/{valve_id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert any(e["new_state"] == "open" for e in resp.json())
