from httpx import AsyncClient

from tests.conftest import auth_header


# ─── Audit Logging ────────────────────────────────────────────────

async def test_api_calls_are_logged(client: AsyncClient, admin_user):
    """API calls should create audit log entries."""
    _, token = admin_user

    # Make a few API calls
    await client.get("/api/auth/me", headers=auth_header(token))
    await client.get("/api/users/", headers=auth_header(token))

    # Check audit logs
    response = await client.get("/api/audit/logs", headers=auth_header(token))
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 2

    # Logs should be ordered by timestamp descending (newest first)
    endpoints = [log["endpoint"] for log in logs]
    assert "/api/audit/logs" in endpoints or "/api/users/" in endpoints


async def test_audit_log_contains_expected_fields(client: AsyncClient, admin_user):
    _, token = admin_user

    # Make a call
    await client.get("/api/auth/me", headers=auth_header(token))

    # Fetch logs
    response = await client.get("/api/audit/logs", headers=auth_header(token))
    logs = response.json()
    assert len(logs) >= 1

    log = logs[0]
    assert "id" in log
    assert "method" in log
    assert "endpoint" in log
    assert "response_status" in log
    assert "timestamp" in log
    assert "duration_ms" in log


async def test_audit_log_masks_passwords(client: AsyncClient, admin_user):
    """Passwords in request bodies should be masked."""
    _, token = admin_user

    # Login call contains password
    await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "admin123",
    })

    # Check that password is masked in logs
    response = await client.get("/api/audit/logs", headers=auth_header(token))
    logs = response.json()

    login_logs = [l for l in logs if l["endpoint"] == "/api/auth/login"]
    assert len(login_logs) >= 1

    body = login_logs[0]["request_body"]
    assert "admin123" not in body
    assert "***" in body


async def test_audit_log_records_user_id(client: AsyncClient, admin_user):
    """Authenticated requests should have user_id in the log."""
    user, token = admin_user

    await client.get("/api/auth/me", headers=auth_header(token))

    response = await client.get("/api/audit/logs", headers=auth_header(token))
    logs = response.json()

    me_logs = [l for l in logs if l["endpoint"] == "/api/auth/me"]
    assert len(me_logs) >= 1
    assert me_logs[0]["user_id"] == user.id


async def test_unauthenticated_requests_logged_without_user(client: AsyncClient, admin_user):
    """Unauthenticated requests should have user_id=None."""
    _, token = admin_user

    # Unauthenticated call
    await client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "wrong123",
    })

    response = await client.get("/api/audit/logs", headers=auth_header(token))
    logs = response.json()

    login_logs = [l for l in logs if l["endpoint"] == "/api/auth/login"]
    assert len(login_logs) >= 1
    assert login_logs[0]["user_id"] is None


# ─── Audit Log Filtering ─────────────────────────────────────────

async def test_filter_by_method(client: AsyncClient, admin_user):
    _, token = admin_user

    # Make GET and POST calls
    await client.get("/api/auth/me", headers=auth_header(token))
    await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "admin123",
    })

    # Filter by POST
    response = await client.get(
        "/api/audit/logs",
        headers=auth_header(token),
        params={"method": "POST"},
    )
    logs = response.json()
    assert all(log["method"] == "POST" for log in logs)


async def test_filter_by_endpoint(client: AsyncClient, admin_user):
    _, token = admin_user

    await client.get("/api/auth/me", headers=auth_header(token))

    response = await client.get(
        "/api/audit/logs",
        headers=auth_header(token),
        params={"endpoint_contains": "/auth/me"},
    )
    logs = response.json()
    assert all("/auth/me" in log["endpoint"] for log in logs)


async def test_filter_by_status_range(client: AsyncClient, admin_user):
    _, token = admin_user

    # Generate a 401
    await client.get("/api/auth/me")
    # Generate a 200
    await client.get("/api/auth/me", headers=auth_header(token))

    # Filter for errors only
    response = await client.get(
        "/api/audit/logs",
        headers=auth_header(token),
        params={"status_min": 400, "status_max": 499},
    )
    logs = response.json()
    assert all(400 <= log["response_status"] <= 499 for log in logs)


async def test_audit_log_pagination(client: AsyncClient, admin_user):
    _, token = admin_user

    # Make several calls
    for _ in range(5):
        await client.get("/api/auth/me", headers=auth_header(token))

    # Get first 2
    response = await client.get(
        "/api/audit/logs",
        headers=auth_header(token),
        params={"limit": 2, "offset": 0},
    )
    page1 = response.json()
    assert len(page1) == 2

    # Get next 2
    response = await client.get(
        "/api/audit/logs",
        headers=auth_header(token),
        params={"limit": 2, "offset": 2},
    )
    page2 = response.json()
    assert len(page2) == 2

    # Pages should be different
    assert page1[0]["id"] != page2[0]["id"]


# ─── Audit Log Count ─────────────────────────────────────────────

async def test_audit_log_count(client: AsyncClient, admin_user):
    _, token = admin_user

    await client.get("/api/auth/me", headers=auth_header(token))

    response = await client.get("/api/audit/logs/count", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["count"] >= 1


# ─── Access Control ───────────────────────────────────────────────

async def test_normal_user_cannot_access_audit_logs(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.get("/api/audit/logs", headers=auth_header(token))
    assert response.status_code == 403


async def test_unauthenticated_cannot_access_audit_logs(client: AsyncClient):
    response = await client.get("/api/audit/logs")
    assert response.status_code == 401


# ─── Health endpoint is NOT logged ────────────────────────────────

async def test_health_endpoint_not_logged(client: AsyncClient, admin_user):
    _, token = admin_user

    await client.get("/api/health")

    response = await client.get("/api/audit/logs", headers=auth_header(token))
    logs = response.json()
    health_logs = [l for l in logs if l["endpoint"] == "/api/health"]
    assert len(health_logs) == 0

