"""Tests for the unified timeline and the audit-log hash chain."""
from __future__ import annotations

from datetime import date

from httpx import AsyncClient

# ─── Timeline ──────────────────────────────────────────────────────


async def test_timeline_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get(
        "/api/timeline/", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total"] == 0


async def test_timeline_includes_finance_event(
    client: AsyncClient, admin_user, normal_user
):
    user, user_token = normal_user
    await client.post(
        "/api/finance/payments/",
        json={
            "amount_cents": 5000,
            "payment_type": "transfer",
            "payment_date": date.today().isoformat(),
            "description": "Miete Q1",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    _, admin_token = admin_user
    resp = await client.get(
        "/api/timeline/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    types = {e["event_type"] for e in resp.json()["events"]}
    assert "payment" in types


async def test_timeline_includes_duty_log(
    client: AsyncClient, admin_user, normal_user
):
    _, user_token = normal_user
    await client.post(
        "/api/duty/logs",
        json={"date": date.today().isoformat(), "hours": 1.5, "description": "Giessen"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    _, admin_token = admin_user
    resp = await client.get(
        "/api/timeline/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    types = {e["event_type"] for e in resp.json()["events"]}
    assert "duty_log" in types


async def test_timeline_date_filter(
    client: AsyncClient, admin_user
):
    """Events outside the window must not appear."""
    _, token = admin_user
    today = date.today().isoformat()
    await client.post(
        "/api/finance/payments/",
        json={
            "amount_cents": 1000,
            "payment_type": "transfer",
            "payment_date": today,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Date window completely in the past → empty
    resp = await client.get(
        "/api/timeline/",
        params={"date_from": "2000-01-01T00:00:00", "date_to": "2000-12-31T23:59:59"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["events"] == []


async def test_timeline_event_type_filter(
    client: AsyncClient, admin_user
):
    _, token = admin_user
    today = date.today().isoformat()
    await client.post(
        "/api/finance/payments/",
        json={"amount_cents": 1000, "payment_type": "transfer", "payment_date": today},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/timeline/", params={"event_type": "payment"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert all(e["event_type"] == "payment" for e in resp.json()["events"])

    # Negative filter: nothing of an unrelated type
    resp = await client.get(
        "/api/timeline/", params={"event_type": "harvest"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["events"] == []


async def test_timeline_pagination(
    client: AsyncClient, admin_user
):
    _, token = admin_user
    today = date.today().isoformat()
    for i in range(5):
        await client.post(
            "/api/finance/payments/",
            json={"amount_cents": 100 + i, "payment_type": "transfer", "payment_date": today},
            headers={"Authorization": f"Bearer {token}"},
        )
    page1 = await client.get(
        "/api/timeline/", params={"limit": 2, "offset": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    page2 = await client.get(
        "/api/timeline/", params={"limit": 2, "offset": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(page1.json()["events"]) == 2
    assert len(page2.json()["events"]) == 2
    # Different rows
    assert page1.json()["events"][0]["id"] != page2.json()["events"][0]["id"]


async def test_timeline_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/timeline/")
    assert resp.status_code == 401


# ─── Audit chain ───────────────────────────────────────────────────


async def test_audit_chain_valid_after_activity(client: AsyncClient, admin_user):
    """Performing a few API calls must yield a valid hash chain."""
    _, token = admin_user
    for _ in range(3):
        await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(
        "/api/audit/chain/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True
    assert resp.json()["breaks"] == []


async def test_audit_chain_detects_tampering(client: AsyncClient, admin_user):
    """Manually mutating an audit entry breaks the chain."""
    from sqlalchemy import select

    from app.audit.models import AuditLog
    from tests.conftest import test_session_factory

    _, token = admin_user
    await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    # Reach into the test DB and corrupt the last entry
    async with test_session_factory() as db:
        result = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
        last = result.scalar_one()
        original = last.endpoint
        last.endpoint = "/hacked"
        await db.commit()

    resp = await client.get(
        "/api/audit/chain/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["valid"] is False
    assert any(b["reason"].startswith("entry_hash") for b in resp.json()["breaks"])

    # Restore for other tests
    async with test_session_factory() as db:
        result = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
        last = result.scalar_one()
        last.endpoint = original
        await db.commit()


async def test_audit_export_csv(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(
        "/api/audit/export.csv", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text
    assert "endpoint" in body  # header line
    assert "/api/auth/me" in body


async def test_audit_chain_verify_requires_admin(client: AsyncClient, normal_user):
    _, token = normal_user
    resp = await client.get(
        "/api/audit/chain/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
