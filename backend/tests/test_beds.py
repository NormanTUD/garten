from httpx import AsyncClient

from tests.conftest import auth_header


async def _create_garden(client: AsyncClient, token: str) -> int:
    resp = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={"name": "Testgarten"},
    )
    return resp.json()["id"]


async def _create_plant(client: AsyncClient, token: str) -> int:
    resp = await client.post(
        "/api/plants/",
        headers=auth_header(token),
        json={"name": "Tomate", "variety": "Roma"},
    )
    return resp.json()["id"]


async def _create_bed(client: AsyncClient, token: str, garden_id: int) -> int:
    resp = await client.post(
        "/api/beds/",
        headers=auth_header(token),
        json={"garden_id": garden_id, "name": "Beet 1"},
    )
    return resp.json()["id"]


# ─── Create Bed ───────────────────────────────────────────────────

async def test_create_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)

    response = await client.post(
        "/api/beds/",
        headers=auth_header(token),
        json={
            "garden_id": garden_id,
            "name": "Beet 1",
            "description": "Tomaten und Gurken",
            "area_sqm": 12.5,
            "soil_type": "loam",
            "sun_exposure": "full_sun",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beet 1"
    assert data["garden_id"] == garden_id
    assert data["area_sqm"] == 12.5
    assert data["sun_exposure"] == "full_sun"


async def test_create_bed_with_geojson(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)

    geojson = {
        "type": "Polygon",
        "coordinates": [[[12.37, 51.34], [12.38, 51.34], [12.38, 51.35], [12.37, 51.34]]],
    }

    response = await client.post(
        "/api/beds/",
        headers=auth_header(token),
        json={
            "garden_id": garden_id,
            "name": "Polygon-Beet",
            "geometry": geojson,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["geometry"]["type"] == "Polygon"
    assert len(data["geometry"]["coordinates"][0]) == 4


async def test_create_bed_invalid_garden(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/beds/",
        headers=auth_header(token),
        json={"garden_id": 9999, "name": "Orphan Bed"},
    )
    assert response.status_code == 404


async def test_create_bed_invalid_sun_exposure(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    response = await client.post(
        "/api/beds/",
        headers=auth_header(token),
        json={
            "garden_id": garden_id,
            "name": "Bad Sun",
            "sun_exposure": "moonlight",
        },
    )
    assert response.status_code == 422


async def test_create_bed_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/beds/",
        json={"garden_id": 1, "name": "Nope"},
    )
    assert response.status_code == 401


# ─── List Beds ────────────────────────────────────────────────────

async def test_list_beds(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)

    await client.post(
        "/api/beds/", headers=auth_header(token),
        json={"garden_id": garden_id, "name": "Beet A"},
    )
    await client.post(
        "/api/beds/", headers=auth_header(token),
        json={"garden_id": garden_id, "name": "Beet B"},
    )

    response = await client.get(
        "/api/beds/", headers=auth_header(token), params={"garden_id": garden_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Beet A"
    assert data[1]["name"] == "Beet B"


async def test_list_beds_invalid_garden(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get(
        "/api/beds/", headers=auth_header(token), params={"garden_id": 9999}
    )
    assert response.status_code == 404


# ─── Get Bed ──────────────────────────────────────────────────────

async def test_get_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    response = await client.get(f"/api/beds/{bed_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["name"] == "Beet 1"


async def test_get_bed_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/beds/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update Bed ───────────────────────────────────────────────────

async def test_update_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    response = await client.patch(
        f"/api/beds/{bed_id}",
        headers=auth_header(token),
        json={"name": "Umbenannt", "area_sqm": 20.0},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Umbenannt"
    assert response.json()["area_sqm"] == 20.0


async def test_update_bed_geometry(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    geojson = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }
    response = await client.patch(
        f"/api/beds/{bed_id}",
        headers=auth_header(token),
        json={"geometry": geojson},
    )
    assert response.status_code == 200
    assert response.json()["geometry"]["type"] == "Polygon"


async def test_update_bed_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/beds/9999", headers=auth_header(token), json={"name": "Ghost"}
    )
    assert response.status_code == 404


# ─── Delete Bed ───────────────────────────────────────────────────

async def test_delete_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    response = await client.delete(f"/api/beds/{bed_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/beds/{bed_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_bed_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/beds/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Cascade: delete garden deletes beds ──────────────────────────

async def test_delete_garden_cascades_beds(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    await client.delete(f"/api/gardens/{garden_id}", headers=auth_header(token))

    get_resp = await client.get(f"/api/beds/{bed_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


# ─── Bed Plantings ────────────────────────────────────────────────

async def test_create_planting(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)

    response = await client.post(
        "/api/plantings/",
        headers=auth_header(token),
        json={
            "bed_id": bed_id,
            "plant_id": plant_id,
            "planted_at": "2026-03-15",
            "expected_harvest_date": "2026-07-01",
            "status": "active",
            "notes": "Reihe 1",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bed_id"] == bed_id
    assert data["plant_id"] == plant_id
    assert data["status"] == "active"
    assert data["plant"]["name"] == "Tomate"
    assert data["plant"]["variety"] == "Roma"


async def test_create_planting_invalid_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    plant_id = await _create_plant(client, token)
    response = await client.post(
        "/api/plantings/",
        headers=auth_header(token),
        json={"bed_id": 9999, "plant_id": plant_id},
    )
    assert response.status_code == 404


async def test_create_planting_invalid_plant(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    response = await client.post(
        "/api/plantings/",
        headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": 9999},
    )
    assert response.status_code == 404


async def test_create_planting_invalid_status(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)
    response = await client.post(
        "/api/plantings/",
        headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": plant_id, "status": "dead"},
    )
    assert response.status_code == 422


async def test_list_plantings(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)

    await client.post(
        "/api/plantings/", headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": plant_id, "notes": "Planting 1"},
    )
    await client.post(
        "/api/plantings/", headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": plant_id, "notes": "Planting 2"},
    )

    response = await client.get(
        "/api/plantings/", headers=auth_header(token), params={"bed_id": bed_id}
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_planting(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)

    create_resp = await client.post(
        "/api/plantings/", headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": plant_id},
    )
    planting_id = create_resp.json()["id"]

    response = await client.get(f"/api/plantings/{planting_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["id"] == planting_id


async def test_get_planting_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/plantings/9999", headers=auth_header(token))
    assert response.status_code == 404


async def test_update_planting(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)

    create_resp = await client.post(
        "/api/plantings/", headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": plant_id, "status": "active"},
    )
    planting_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/plantings/{planting_id}",
        headers=auth_header(token),
        json={"status": "harvested", "notes": "Ernte war gut"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "harvested"
    assert response.json()["notes"] == "Ernte war gut"


async def test_update_planting_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/plantings/9999", headers=auth_header(token), json={"status": "harvested"}
    )
    assert response.status_code == 404


async def test_delete_planting(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)

    create_resp = await client.post(
        "/api/plantings/", headers=auth_header(token),
        json={"bed_id": bed_id, "plant_id": plant_id},
    )
    planting_id = create_resp.json()["id"]

    response = await client.delete(f"/api/plantings/{planting_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/plantings/{planting_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_planting_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/plantings/9999", headers=auth_header(token))
    assert response.status_code == 404

