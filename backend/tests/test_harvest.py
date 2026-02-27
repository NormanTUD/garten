from httpx import AsyncClient

from tests.conftest import auth_header


async def _create_garden(client: AsyncClient, token: str) -> int:
    resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Testgarten"}
    )
    return resp.json()["id"]


async def _create_bed(client: AsyncClient, token: str, garden_id: int) -> int:
    resp = await client.post(
        "/api/beds/", headers=auth_header(token),
        json={"garden_id": garden_id, "name": "Beet 1"},
    )
    return resp.json()["id"]


async def _create_plant(client: AsyncClient, token: str) -> int:
    resp = await client.post(
        "/api/plants/", headers=auth_header(token),
        json={"name": "Tomate", "variety": "Roma"},
    )
    return resp.json()["id"]


# ─── Create Harvest ───────────────────────────────────────────────

async def test_create_harvest(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)
    plant_id = await _create_plant(client, token)

    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={
            "bed_id": bed_id,
            "plant_id": plant_id,
            "amount": 2.5,
            "unit": "kg",
            "quality_rating": 4,
            "date": "2026-07-15",
            "notes": "Schöne reife Tomaten",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 2.5
    assert data["unit"] == "kg"
    assert data["quality_rating"] == 4
    assert data["date"] == "2026-07-15"
    assert data["user"]["display_name"] == "Test Admin"
    assert data["bed"]["name"] == "Beet 1"
    assert data["plant"]["name"] == "Tomate"


async def test_create_harvest_minimal(client: AsyncClient, admin_user):
    """Harvest without bed or plant reference."""
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={
            "amount": 5,
            "unit": "stueck",
            "date": "2026-07-15",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bed"] is None
    assert data["plant"] is None
    assert data["amount"] == 5


async def test_create_harvest_invalid_unit(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"amount": 1, "unit": "tonnen", "date": "2026-07-15"},
    )
    assert response.status_code == 422


async def test_create_harvest_invalid_quality(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"amount": 1, "unit": "kg", "date": "2026-07-15", "quality_rating": 6},
    )
    assert response.status_code == 422


async def test_create_harvest_zero_amount(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"amount": 0, "unit": "kg", "date": "2026-07-15"},
    )
    assert response.status_code == 422


async def test_create_harvest_invalid_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"bed_id": 9999, "amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    assert response.status_code == 404


async def test_create_harvest_invalid_plant(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"plant_id": 9999, "amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    assert response.status_code == 404


async def test_create_harvest_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/harvests/",
        json={"amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    assert response.status_code == 401


# ─── List Harvests ────────────────────────────────────────────────

async def test_list_harvests(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 1, "unit": "kg", "date": "2026-07-10"},
    )
    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 3, "unit": "stueck", "date": "2026-07-15"},
    )

    response = await client.get("/api/harvests/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by date desc
    assert data[0]["date"] == "2026-07-15"
    assert data[1]["date"] == "2026-07-10"


async def test_list_harvests_filter_by_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"bed_id": bed_id, "amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 2, "unit": "kg", "date": "2026-07-15"},
    )

    response = await client.get(
        "/api/harvests/", headers=auth_header(token), params={"bed_id": bed_id}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_harvests_filter_by_date_range(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 1, "unit": "kg", "date": "2026-06-01"},
    )
    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 2, "unit": "kg", "date": "2026-07-15"},
    )
    await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 3, "unit": "kg", "date": "2026-08-30"},
    )

    response = await client.get(
        "/api/harvests/", headers=auth_header(token),
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 2


async def test_list_harvests_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/harvests/", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


# ─── Get Harvest ──────────────────────────────────────────────────

async def test_get_harvest(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    harvest_id = create_resp.json()["id"]

    response = await client.get(f"/api/harvests/{harvest_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["id"] == harvest_id


async def test_get_harvest_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/harvests/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update Harvest ───────────────────────────────────────────────

async def test_update_harvest(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    harvest_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/harvests/{harvest_id}",
        headers=auth_header(token),
        json={"amount": 3.5, "quality_rating": 5, "notes": "Korrektur"},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 3.5
    assert response.json()["quality_rating"] == 5
    assert response.json()["notes"] == "Korrektur"


async def test_update_harvest_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/harvests/9999", headers=auth_header(token), json={"amount": 1}
    )
    assert response.status_code == 404


# ─── Delete Harvest ───────────────────────────────────────────────

async def test_delete_harvest(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"amount": 1, "unit": "kg", "date": "2026-07-15"},
    )
    harvest_id = create_resp.json()["id"]

    response = await client.delete(f"/api/harvests/{harvest_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/harvests/{harvest_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_harvest_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/harvests/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Normal user can use harvests ─────────────────────────────────

async def test_normal_user_can_create_harvest(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"amount": 2, "unit": "bund", "date": "2026-07-15"},
    )
    assert response.status_code == 201
    assert response.json()["user"]["display_name"] == "Test User"

