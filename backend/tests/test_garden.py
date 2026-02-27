from httpx import AsyncClient

from tests.conftest import auth_header


# ─── Create Garden ────────────────────────────────────────────────

async def test_create_garden(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={
            "name": "Schrebergarten Am Bach",
            "description": "Unser Vereinsgarten",
            "location_lat": 51.3406,
            "location_lng": 12.3747,
            "total_area_sqm": 500.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Schrebergarten Am Bach"
    assert data["location_lat"] == 51.3406
    assert data["total_area_sqm"] == 500.0
    assert "id" in data
    assert "created_at" in data


async def test_create_garden_minimal(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={"name": "Kleingarten"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Kleingarten"
    assert data["description"] is None
    assert data["location_lat"] is None


async def test_create_garden_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/gardens/",
        json={"name": "Test"},
    )
    assert response.status_code == 401


async def test_create_garden_empty_name_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={"name": ""},
    )
    assert response.status_code == 422


async def test_create_garden_invalid_lat_rejected(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={"name": "Test", "location_lat": 100.0},
    )
    assert response.status_code == 422


# ─── List Gardens ─────────────────────────────────────────────────

async def test_list_gardens(client: AsyncClient, admin_user):
    _, token = admin_user
    # Create two gardens
    await client.post("/api/gardens/", headers=auth_header(token), json={"name": "Garten A"})
    await client.post("/api/gardens/", headers=auth_header(token), json={"name": "Garten B"})

    response = await client.get("/api/gardens/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by name
    assert data[0]["name"] == "Garten A"
    assert data[1]["name"] == "Garten B"


async def test_list_gardens_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/gardens/", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


# ─── Get Garden ───────────────────────────────────────────────────

async def test_get_garden(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Mein Garten"}
    )
    garden_id = create_resp.json()["id"]

    response = await client.get(f"/api/gardens/{garden_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["name"] == "Mein Garten"


async def test_get_garden_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/gardens/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update Garden ────────────────────────────────────────────────

async def test_update_garden(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Alt"}
    )
    garden_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/gardens/{garden_id}",
        headers=auth_header(token),
        json={"name": "Neu", "total_area_sqm": 250.5},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Neu"
    assert response.json()["total_area_sqm"] == 250.5


async def test_update_garden_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/gardens/9999",
        headers=auth_header(token),
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


# ─── Delete Garden ────────────────────────────────────────────────

async def test_delete_garden(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Zum Löschen"}
    )
    garden_id = create_resp.json()["id"]

    response = await client.delete(f"/api/gardens/{garden_id}", headers=auth_header(token))
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/gardens/{garden_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_garden_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/gardens/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Normal user can also use gardens ─────────────────────────────

async def test_normal_user_can_create_garden(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={"name": "User-Garten"},
    )
    assert response.status_code == 201

