from httpx import AsyncClient

from tests.conftest import auth_header


# ─── List Users (Admin only) ─────────────────────────────────────

async def test_list_users_as_admin(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/users/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["username"] == "testadmin"


async def test_list_users_as_normal_user_forbidden(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.get("/api/users/", headers=auth_header(token))
    assert response.status_code == 403


async def test_list_users_unauthenticated(client: AsyncClient):
    response = await client.get("/api/users/")
    assert response.status_code == 401


# ─── Create User (Admin only) ────────────────────────────────────

async def test_create_user_as_admin(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "newgardener",
            "password": "garden123",
            "display_name": "New Gardener",
            "role": "user",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newgardener"
    assert data["display_name"] == "New Gardener"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "id" in data


async def test_create_user_duplicate_username(client: AsyncClient, admin_user):
    _, token = admin_user
    # Create first user
    await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "duplicate",
            "password": "pass1234",
            "display_name": "First",
            "role": "user",
        },
    )
    # Try to create with same username
    response = await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "duplicate",
            "password": "pass5678",
            "display_name": "Second",
            "role": "user",
        },
    )
    assert response.status_code == 409


async def test_create_user_as_normal_user_forbidden(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "sneaky",
            "password": "pass1234",
            "display_name": "Sneaky User",
            "role": "user",
        },
    )
    assert response.status_code == 403

"""
async def test_create_user_invalid_username_rejected(client: AsyncClient, admin_user):
    " ""Username must match pattern ^[a-zA-Z0-9_-]+$"" "
    _, token = admin_user
    response = await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "bad user!",
            "password": "pass1234",
            "display_name": "Bad",
            "role": "user",
        },
    )
    assert response.status_code == 422
"""

async def test_create_user_invalid_role_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "hacker",
            "password": "pass1234",
            "display_name": "Hacker",
            "role": "superadmin",
        },
    )
    assert response.status_code == 422


async def test_create_user_short_password_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/users/",
        headers=auth_header(token),
        json={
            "username": "shortpw",
            "password": "ab",
            "display_name": "Short PW",
            "role": "user",
        },
    )
    assert response.status_code == 422


# ─── Get Single User (Admin only) ────────────────────────────────

async def test_get_user_by_id(client: AsyncClient, admin_user):
    user, token = admin_user
    response = await client.get(f"/api/users/{user.id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["username"] == "testadmin"


async def test_get_user_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/users/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update User (Admin only) ────────────────────────────────────

async def test_update_user_display_name(client: AsyncClient, admin_user, normal_user):
    user, _ = normal_user
    _, admin_token = admin_user
    response = await client.patch(
        f"/api/users/{user.id}",
        headers=auth_header(admin_token),
        json={"display_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated Name"


async def test_update_user_role(client: AsyncClient, admin_user, normal_user):
    user, _ = normal_user
    _, admin_token = admin_user
    response = await client.patch(
        f"/api/users/{user.id}",
        headers=auth_header(admin_token),
        json={"role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_deactivate_user(client: AsyncClient, admin_user, normal_user):
    user, _ = normal_user
    _, admin_token = admin_user
    response = await client.patch(
        f"/api/users/{user.id}",
        headers=auth_header(admin_token),
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_deactivated_user_cannot_login(client: AsyncClient, admin_user, normal_user):
    user, _ = normal_user
    _, admin_token = admin_user

    # Deactivate user
    await client.patch(
        f"/api/users/{user.id}",
        headers=auth_header(admin_token),
        json={"is_active": False},
    )

    # Try to login
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "user1234",
    })
    assert response.status_code == 401


async def test_update_user_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/users/9999",
        headers=auth_header(token),
        json={"display_name": "Ghost"},
    )
    assert response.status_code == 404


async def test_update_user_as_normal_user_forbidden(client: AsyncClient, admin_user, normal_user):
    admin, _ = admin_user
    _, user_token = normal_user
    response = await client.patch(
        f"/api/users/{admin.id}",
        headers=auth_header(user_token),
        json={"role": "user"},
    )
    assert response.status_code == 403


# ─── Admin Password Reset ────────────────────────────────────────

async def test_admin_reset_user_password(client: AsyncClient, admin_user, normal_user):
    user, _ = normal_user
    _, admin_token = admin_user

    response = await client.put(
        f"/api/users/{user.id}/password",
        headers=auth_header(admin_token),
        json={"new_password": "resetted123"},
    )
    assert response.status_code == 204

    # Verify new password works
    login_resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "resetted123",
    })
    assert login_resp.status_code == 200


async def test_admin_reset_password_user_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.put(
        "/api/users/9999/password",
        headers=auth_header(token),
        json={"new_password": "whatever123"},
    )
    assert response.status_code == 404


async def test_normal_user_cannot_reset_others_password(
    client: AsyncClient, admin_user, normal_user
):
    admin, _ = admin_user
    _, user_token = normal_user
    response = await client.put(
        f"/api/users/{admin.id}/password",
        headers=auth_header(user_token),
        json={"new_password": "hacked123"},
    )
    assert response.status_code == 403


# ─── Created user can log in ─────────────────────────────────────

async def test_newly_created_user_can_login(client: AsyncClient, admin_user):
    _, admin_token = admin_user

    # Admin creates a new user
    await client.post(
        "/api/users/",
        headers=auth_header(admin_token),
        json={
            "username": "gardener1",
            "password": "flowers123",
            "display_name": "Gärtner Eins",
            "role": "user",
        },
    )

    # New user logs in
    response = await client.post("/api/auth/login", json={
        "username": "gardener1",
        "password": "flowers123",
    })
    assert response.status_code == 200

    # New user can access /me
    token = response.json()["access_token"]
    me_resp = await client.get("/api/auth/me", headers=auth_header(token))
    assert me_resp.status_code == 200
    assert me_resp.json()["display_name"] == "Gärtner Eins"
    assert me_resp.json()["role"] == "user"

