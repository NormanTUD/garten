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


# ═══════════════════════════════════════════════════════════════════
# Watering Events
# ═══════════════════════════════════════════════════════════════════

# ─── Create ───────────────────────────────────────────────────────

async def test_create_watering_event(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={
            "bed_id": bed_id,
            "started_at": "2026-07-15T08:30:00Z",
            "duration_minutes": 30,
            "water_amount_liters": 50.0,
            "method": "manual",
            "weather_temp_c": 28.5,
            "weather_humidity_pct": 45.0,
            "weather_rain_mm": 0,
            "weather_description": "Sonnig",
            "soil_moisture_before": 20.0,
            "soil_moisture_after": 65.0,
            "notes": "Morgens gegossen",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["duration_minutes"] == 30
    assert data["water_amount_liters"] == 50.0
    assert data["method"] == "manual"
    assert data["weather_temp_c"] == 28.5
    assert data["soil_moisture_before"] == 20.0
    assert data["soil_moisture_after"] == 65.0
    assert data["user"]["display_name"] == "Test Admin"
    assert data["bed"]["name"] == "Beet 1"


async def test_create_watering_event_minimal(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"started_at": "2026-07-15T08:30:00Z"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bed"] is None
    assert data["duration_minutes"] is None
    assert data["weather_temp_c"] is None


async def test_create_watering_event_invalid_method(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"started_at": "2026-07-15T08:30:00Z", "method": "sprinkler"},
    )
    assert response.status_code == 422


async def test_create_watering_event_invalid_humidity(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"started_at": "2026-07-15T08:30:00Z", "weather_humidity_pct": 150},
    )
    assert response.status_code == 422


async def test_create_watering_event_invalid_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"bed_id": 9999, "started_at": "2026-07-15T08:30:00Z"},
    )
    assert response.status_code == 404

async def test_create_watering_event_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/watering/",
        json={"started_at": "2026-07-15T08:30:00Z"},
    )
    assert response.status_code == 401


# ─── List ─────────────────────────────────────────────────────────

async def test_list_watering_events(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z"},
    )
    await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"started_at": "2026-07-16T09:00:00Z"},
    )

    response = await client.get("/api/watering/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by started_at desc
    assert data[0]["started_at"] > data[1]["started_at"]


async def test_list_watering_events_filter_by_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"bed_id": bed_id, "started_at": "2026-07-15T08:00:00Z"},
    )
    await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"started_at": "2026-07-15T09:00:00Z"},
    )

    response = await client.get(
        "/api/watering/", headers=auth_header(token), params={"bed_id": bed_id}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_watering_events_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/watering/", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


# ─── Get ──────────────────────────────────────────────────────────

async def test_get_watering_event(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z"},
    )
    event_id = create_resp.json()["id"]

    response = await client.get(f"/api/watering/{event_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["id"] == event_id


async def test_get_watering_event_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/watering/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update ───────────────────────────────────────────────────────

async def test_update_watering_event(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z", "duration_minutes": 10},
    )
    event_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/watering/{event_id}",
        headers=auth_header(token),
        json={"duration_minutes": 45, "water_amount_liters": 100, "notes": "Korrektur"},
    )
    assert response.status_code == 200
    assert response.json()["duration_minutes"] == 45
    assert response.json()["water_amount_liters"] == 100
    assert response.json()["notes"] == "Korrektur"


async def test_update_watering_event_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/watering/9999", headers=auth_header(token),
        json={"duration_minutes": 10},
    )
    assert response.status_code == 404


# ─── Delete ───────────────────────────────────────────────────────

async def test_delete_watering_event(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z"},
    )
    event_id = create_resp.json()["id"]

    response = await client.delete(f"/api/watering/{event_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/watering/{event_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_watering_event_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/watering/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Normal user ──────────────────────────────────────────────────

async def test_normal_user_can_create_watering_event(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z", "duration_minutes": 20},
    )
    assert response.status_code == 201
    assert response.json()["user"]["display_name"] == "Test User"


# ═══════════════════════════════════════════════════════════════════
# Fertilizing Events
# ═══════════════════════════════════════════════════════════════════

# ─── Create ───────────────────────────────────────────────────────

async def test_create_fertilizing_event(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    response = await client.post(
        "/api/fertilizing/",
        headers=auth_header(token),
        json={
            "bed_id": bed_id,
            "fertilizer_type": "Kompost",
            "amount": 5.0,
            "unit": "kg",
            "date": "2026-04-10",
            "notes": "Frühjahrsdüngung",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["fertilizer_type"] == "Kompost"
    assert data["amount"] == 5.0
    assert data["unit"] == "kg"
    assert data["date"] == "2026-04-10"
    assert data["user"]["display_name"] == "Test Admin"
    assert data["bed"]["name"] == "Beet 1"


async def test_create_fertilizing_event_minimal(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/fertilizing/",
        headers=auth_header(token),
        json={"fertilizer_type": "Hornspäne", "date": "2026-04-10"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bed"] is None
    assert data["amount"] is None
    assert data["unit"] is None


async def test_create_fertilizing_event_invalid_unit(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/fertilizing/",
        headers=auth_header(token),
        json={"fertilizer_type": "Test", "date": "2026-04-10", "unit": "tonnen"},
    )
    assert response.status_code == 422


async def test_create_fertilizing_event_invalid_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/fertilizing/",
        headers=auth_header(token),
        json={"bed_id": 9999, "fertilizer_type": "Test", "date": "2026-04-10"},
    )
    assert response.status_code == 404


async def test_create_fertilizing_event_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/fertilizing/",
        json={"fertilizer_type": "Test", "date": "2026-04-10"},
    )
    assert response.status_code == 401


# ─── List ─────────────────────────────────────────────────────────

async def test_list_fertilizing_events(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"fertilizer_type": "Kompost", "date": "2026-04-10"},
    )
    await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"fertilizer_type": "Hornspäne", "date": "2026-05-15"},
    )

    response = await client.get("/api/fertilizing/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Sorted by date desc
    assert data[0]["date"] == "2026-05-15"
    assert data[1]["date"] == "2026-04-10"


async def test_list_fertilizing_events_filter_by_bed(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_id = await _create_garden(client, token)
    bed_id = await _create_bed(client, token, garden_id)

    await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"bed_id": bed_id, "fertilizer_type": "Kompost", "date": "2026-04-10"},
    )
    await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"fertilizer_type": "Hornspäne", "date": "2026-04-10"},
    )

    response = await client.get(
        "/api/fertilizing/", headers=auth_header(token), params={"bed_id": bed_id}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_fertilizing_events_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/fertilizing/", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


# ─── Get ──────────────────────────────────────────────────────────

async def test_get_fertilizing_event(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"fertilizer_type": "Kompost", "date": "2026-04-10"},
    )
    event_id = create_resp.json()["id"]

    response = await client.get(f"/api/fertilizing/{event_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["id"] == event_id


async def test_get_fertilizing_event_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/fertilizing/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Update ───────────────────────────────────────────────────────

async def test_update_fertilizing_event(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"fertilizer_type": "Kompost", "date": "2026-04-10"},
    )
    event_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/fertilizing/{event_id}",
        headers=auth_header(token),
        json={"amount": 10, "unit": "l", "notes": "Flüssigdünger"},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 10
    assert response.json()["unit"] == "l"
    assert response.json()["notes"] == "Flüssigdünger"


async def test_update_fertilizing_event_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/fertilizing/9999", headers=auth_header(token),
        json={"fertilizer_type": "Ghost"},
    )
    assert response.status_code == 404


# ─── Delete ───────────────────────────────────────────────────────

async def test_delete_fertilizing_event(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post(
        "/api/fertilizing/", headers=auth_header(token),
        json={"fertilizer_type": "Kompost", "date": "2026-04-10"},
    )
    event_id = create_resp.json()["id"]

    response = await client.delete(f"/api/fertilizing/{event_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/fertilizing/{event_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


async def test_delete_fertilizing_event_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/fertilizing/9999", headers=auth_header(token))
    assert response.status_code == 404


# ─── Normal user ──────────────────────────────────────────────────

async def test_normal_user_can_create_fertilizing_event(client: AsyncClient, normal_user):
    _, token = normal_user
    response = await client.post(
        "/api/fertilizing/",
        headers=auth_header(token),
        json={"fertilizer_type": "Biodünger", "date": "2026-04-10"},
    )
    assert response.status_code == 201
    assert response.json()["user"]["display_name"] == "Test User"

