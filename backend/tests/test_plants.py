from httpx import AsyncClient

from tests.conftest import auth_header


# ─── Create Plant ─────────────────────────────────────────────────

async def test_create_plant(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/plants/",
        headers=auth_header(token),
        json={
            "name": "Tomate",
            "variety": "San Marzano",
            "category": "Fruchtgemüse",
            "icon": "🍅",
            "expected_water_needs": "high",
            "growing_season_start": 3,
            "growing_season_end": 9,
            "notes": "Braucht Stütze",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tomate"
    assert data["variety"] == "San Marzano"
    assert data["category"] == "Fruchtgemüse"
    assert data["icon"] == "🍅"
    assert data["expected_water_needs"] == "high"
    assert data["growing_season_start"] == 3
    assert data["growing_season_end"] == 9


async def test_create_plant_minimal(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/plants/",
        headers=auth_header(token),
        json={"name": "Basilikum"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Basilikum"
    assert data["variety"] is None
    assert data["category"] is None


async def test_create_plant_invalid_water_needs(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/plants/",
        headers=auth_header(token),
        json={"name": "Test", "expected_water_needs": "extreme"},
    )
    assert response.status_code == 422


async def test_create_plant_invalid_season_month(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/plants/",
        headers=auth_header(token),
        json={"name": "Test", "growing_season_start": 13},
    )
    assert response.status_code == 422


async def test_create_plant_unauthenticated(client: AsyncClient):
    response = await client.post("/api/plants/", json={"name": "Nope"})
    assert response.status_code == 401


# ─── List Plants ──────────────────────────────────────────────────

async def test_list_plants(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post("/api/plants/", headers=auth_header(token), json={"name": "Zucchini"})
    await client.post("/api/plants/", headers=auth_header(token), json={"name": "Aubergine"})

    response = await client.get("/api/plants/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by name
    assert data[0]["name"] == "Aubergine"
    assert data[1]["name"] == "Zucchini"


async def test_list_plants_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/plants/", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


# ─── Search Plants ────────────────────────────────────────────────

async def test_search_plants_by_name(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post("/api/plants/", headers=auth_header(token), json={"name": "Tomate"})
    await client.post("/api/plants/", headers=auth_header(token), json={"name": "Kartoffel"})
    await client.post(
        "/api/plants/", headers=auth_header(token),
        json={"name": "Cherry-Tomate", "variety": "Sweetie"},
    )

    response = await client.get(
        "/api/plants/", headers=auth_header(token), params={"search": "tomate"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [p["name"] for p in data]
    assert "Tomate" in names
    assert "Cherry-Tomate" in names


async def test_search_plants_by_variety(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/plants/", headers=auth_header(token),
        json={"name": "Tomate", "variety": "Roma"},
    )
    await client.post(
        "/api/plants/", headers=auth_header(token),
        json={"name": "Tomate", "variety": "San Marzano"},
    )

    response = await client.get(
        "/api/plants/", headers=auth_header(token), params={"search": "roma"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["variety"] == "Roma"


async def test_search_plants_no_results(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post("/api/plants/", headers=auth_header(token), json={"name": "Tomate"})

    response = await client.get(
        "/api/plants/", headers=auth_header(token), params={"search": "xyz"}
    )
    assert response.status_code == 200
    assert response.json() == []


# ─── Get Plant ────────────────────────────────────────────────────

async def test_get_plant(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/plants/", headers=auth_header(token), json={"name": "Gurke"}
    )
    plant_id = create_resp.json()["id"]

    response = await client.get(f"/api/plants/{plant_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["name"] == "Gurke"


async def test_get_plant_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/plants/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update Plant ─────────────────────────────────────────────────

async def test_update_plant(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/plants/", headers=auth_header(token), json={"name": "Paprika"}
    )
    plant_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/plants/{plant_id}",
        headers=auth_header(token),
        json={"variety": "Rot", "expected_water_needs": "medium"},
    )
    assert response.status_code == 200
    assert response.json()["variety"] == "Rot"
    assert response.json()["expected_water_needs"] == "medium"
    assert response.json()["name"] == "Paprika"  # unchanged


async def test_update_plant_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/plants/9999", headers=auth_header(token), json={"name": "Ghost"}
    )
    assert response.status_code == 404


# ─── Delete Plant ─────────────────────────────────────────────────

async def test_delete_plant(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/plants/", headers=auth_header(token), json={"name": "Zum Löschen"}
    )
    plant_id = create_resp.json()["id"]

    response = await client.delete(f"/api/plants/{plant_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/plants/{plant_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_plant_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/plants/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Normal user access ──────────────────────────────────────────

async def test_normal_user_can_crud_plants(client: AsyncClient, normal_user):
    _, token = normal_user

    # Create
    resp = await client.post(
        "/api/plants/", headers=auth_header(token), json={"name": "Salat"}
    )
    assert resp.status_code == 201
    plant_id = resp.json()["id"]

    # Read
    resp = await client.get(f"/api/plants/{plant_id}", headers=auth_header(token))
    assert resp.status_code == 200

    # Update
    resp = await client.patch(
        f"/api/plants/{plant_id}",
        headers=auth_header(token),
        json={"variety": "Eisberg"},
    )
    assert resp.status_code == 200

    # List
    resp = await client.get("/api/plants/", headers=auth_header(token))
    assert resp.status_code == 200

