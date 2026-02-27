from httpx import AsyncClient

from tests.conftest import auth_header


# ─── Login ────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient, admin_user):
    """Admin user can log in with correct credentials."""
    response = await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "admin123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, admin_user):
    response = await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "whatever",
    })
    assert response.status_code == 401


async def test_login_short_password_rejected(client: AsyncClient):
    """Pydantic validation rejects passwords shorter than 4 chars."""
    response = await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "ab",
    })
    assert response.status_code == 422


# ─── Token Refresh ────────────────────────────────────────────────

async def test_refresh_token(client: AsyncClient, admin_user):
    # First login to get tokens
    login_resp = await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "admin123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    # Use refresh token to get new access token
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_refresh_with_access_token_fails(client: AsyncClient, admin_user):
    """Using an access token as refresh token should fail."""
    _, token = admin_user
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": token,  # This is an access token, not refresh
    })
    assert response.status_code == 401


async def test_refresh_with_invalid_token_fails(client: AsyncClient):
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": "not.a.valid.token",
    })
    assert response.status_code == 401


# ─── Get Current User ────────────────────────────────────────────

async def test_get_me(client: AsyncClient, admin_user):
    user, token = admin_user
    response = await client.get("/api/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"
    assert data["display_name"] == "Test Admin"
    assert "password_hash" not in data


async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_get_me_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/auth/me",
        headers=auth_header("invalid.token.here"),
    )
    assert response.status_code == 401


# ─── Password Change ─────────────────────────────────────────────

async def test_change_own_password(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.put(
        "/api/auth/me/password",
        headers=auth_header(token),
        json={
            "current_password": "admin123",
            "new_password": "newpassword123",
        },
    )
    assert response.status_code == 204

    # Verify new password works
    login_resp = await client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "newpassword123",
    })
    assert login_resp.status_code == 200


async def test_change_password_wrong_current(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.put(
        "/api/auth/me/password",
        headers=auth_header(token),
        json={
            "current_password": "wrongcurrent",
            "new_password": "newpassword123",
        },
    )
    assert response.status_code == 400
