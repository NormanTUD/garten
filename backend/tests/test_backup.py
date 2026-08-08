"""Tests for the backup & restore module."""
from __future__ import annotations

import io
import tarfile

from httpx import AsyncClient


async def test_export_backup_returns_tarball(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/backup/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/gzip"
    assert "attachment" in resp.headers["content-disposition"]
    payload = resp.content
    assert len(payload) > 100
    # Verify it's a valid tar.gz
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        names = tar.getnames()
    assert any("manifest.json" in n for n in names)


async def test_export_backup_includes_sqlite(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/backup/export", headers={"Authorization": f"Bearer {token}"})
    payload = resp.content
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        names = tar.getnames()
    assert any(n.endswith("gartenapp.db") for n in names)


async def test_export_requires_admin(client: AsyncClient, normal_user):
    _, token = normal_user
    resp = await client.get("/api/backup/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_import_rejects_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/backup/import",
        files={"file": ("empty.tar.gz", b"", "application/gzip")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_import_rejects_invalid_tarball(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/backup/import",
        files={"file": ("bad.tar.gz", b"not-a-real-tarball", "application/gzip")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_round_trip_export_then_import(client: AsyncClient, admin_user):
    """What we export, we can import again."""
    _, token = admin_user

    # Create some data we can verify survives the round-trip
    await client.post(
        "/api/finance/payments/",
        json={
            "amount_cents": 1234,
            "payment_type": "transfer",
            "payment_date": "2026-01-15",
            "description": "Round-trip payment",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Export
    export = await client.get(
        "/api/backup/export", headers={"Authorization": f"Bearer {token}"}
    )
    payload = export.content

    # Import the same payload back
    resp = await client.post(
        "/api/backup/import",
        files={"file": ("backup.tar.gz", payload, "application/gzip")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["database_replaced"] is True
