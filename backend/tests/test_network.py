"""Tests for the network MAC-allowlist module."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

VALID_MACS = [
    "AA:BB:CC:DD:EE:FF",
    "aa:bb:cc:dd:ee:ff",
    "aa-bb-cc-dd-ee-ff",
    "AA.BB.CC.DD.EE.FF",
]


async def test_add_network_device(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:FF", "name": "Pi Cam 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["mac_address"] == "AA:BB:CC:DD:EE:FF"


@pytest.mark.parametrize("mac", VALID_MACS)
async def test_mac_normalization(client: AsyncClient, admin_user, mac):
    """All four common MAC formats should normalize to ``AA:BB:CC:DD:EE:FF``."""
    _, token = admin_user
    resp = await client.post(
        "/api/network/devices",
        json={"mac_address": mac, "name": f"Test {mac}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["mac_address"] == "AA:BB:CC:DD:EE:FF"


async def test_duplicate_mac_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/network/devices",
        json={"mac_address": "11:22:33:44:55:66", "name": "First"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/network/devices",
        json={"mac_address": "11:22:33:44:55:66", "name": "Second"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


async def test_invalid_mac_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/network/devices",
        json={"mac_address": "ZZ:YY:XX:WW:VV:UU", "name": "Bad"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_lookup_known_mac(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:01", "name": "Kamera Nord"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/network/lookup?mac=aa:bb:cc:dd:ee:01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_trusted"] is True
    assert data["device_name"] == "Kamera Nord"


async def test_lookup_unknown_mac(client: AsyncClient, admin_user):
    """An unrecognised MAC must report ``is_trusted=False`` so the camera
    can raise an alert."""
    _, token = admin_user
    resp = await client.get(
        "/api/network/lookup?mac=99:88:77:66:55:44",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_trusted"] is False


async def test_inactive_device_not_trusted(client: AsyncClient, admin_user):
    _, token = admin_user
    create = await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:02", "name": "Old", "is_active": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = create.json()["id"]
    await client.patch(
        f"/api/network/devices/{device_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/network/lookup?mac=AA:BB:CC:DD:EE:02",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["is_active"] is False
    assert resp.json()["is_trusted"] is False


async def test_list_filter_by_type(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:10", "name": "Cam", "device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:11", "name": "Phone", "device_type": "phone"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/network/devices", params={"device_type": "camera"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert all(d["device_type"] == "camera" for d in resp.json())


async def test_untrusted_device(client: AsyncClient, admin_user):
    """A device explicitly flagged ``is_trusted=False`` is never trusted,
    even when active."""
    _, token = admin_user
    await client.post(
        "/api/network/devices",
        json={
            "mac_address": "AA:BB:CC:DD:EE:99",
            "name": "Untrusted",
            "is_trusted": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/network/lookup?mac=AA:BB:CC:DD:EE:99",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["is_trusted"] is False


async def test_delete_network_device(client: AsyncClient, admin_user):
    _, token = admin_user
    create = await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:50", "name": "X"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = create.json()["id"]
    delete = await client.delete(
        f"/api/network/devices/{device_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204


async def test_normal_user_cannot_modify_allowlist(client: AsyncClient, normal_user):
    """Only admins can mutate the allowlist; any authenticated user can read."""
    _, token = normal_user
    resp = await client.post(
        "/api/network/devices",
        json={"mac_address": "AA:BB:CC:DD:EE:77", "name": "X"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

    # Read is allowed
    resp = await client.get(
        "/api/network/devices", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
