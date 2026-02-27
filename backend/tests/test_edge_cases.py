from httpx import AsyncClient

from tests.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════
# Pagination Edge Cases
# ═══════════════════════════════════════════════════════════════════

async def test_harvest_pagination(client: AsyncClient, admin_user):
    """Test limit and offset work correctly for harvests."""
    _, token = admin_user

    # Create 5 harvests
    for i in range(5):
        await client.post(
            "/api/harvests/",
            headers=auth_header(token),
            json={"amount": i + 1, "unit": "kg", "harvest_date": f"2026-07-{10 + i:02d}"},
        )

    # Get first 2
    resp = await client.get(
        "/api/harvests/", headers=auth_header(token), params={"limit": 2, "offset": 0}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Get next 2
    resp = await client.get(
        "/api/harvests/", headers=auth_header(token), params={"limit": 2, "offset": 2}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Get last 1
    resp = await client.get(
        "/api/harvests/", headers=auth_header(token), params={"limit": 2, "offset": 4}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_watering_pagination(client: AsyncClient, admin_user):
    _, token = admin_user

    for i in range(5):
        await client.post(
            "/api/watering/",
            headers=auth_header(token),
            json={"started_at": f"2026-07-{10 + i:02d}T08:00:00Z"},
        )

    resp = await client.get(
        "/api/watering/", headers=auth_header(token), params={"limit": 3}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_fertilizing_pagination(client: AsyncClient, admin_user):
    _, token = admin_user

    for i in range(5):
        await client.post(
            "/api/fertilizing/",
            headers=auth_header(token),
            json={"fertilizer_type": f"Type {i}", "event_date": f"2026-04-{10 + i:02d}"},
        )

    resp = await client.get(
        "/api/fertilizing/", headers=auth_header(token), params={"limit": 2, "offset": 3}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ═══════════════════════════════════════════════════════════════════
# Cross-Module Validation
# ═══════════════════════════════════════════════════════════════════

async def test_harvest_with_deleted_bed_keeps_null(client: AsyncClient, admin_user):
    """When a bed is deleted, harvest.bed_id becomes NULL (SET NULL)."""
    _, token = admin_user

    # Create garden + bed
    garden_resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Test"}
    )
    garden_id = garden_resp.json()["id"]
    bed_resp = await client.post(
        "/api/beds/", headers=auth_header(token),
        json={"garden_id": garden_id, "name": "Beet 1"},
    )
    bed_id = bed_resp.json()["id"]

    # Create harvest referencing bed
    harvest_resp = await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"bed_id": bed_id, "amount": 1, "unit": "kg", "harvest_date": "2026-07-15"},
    )
    harvest_id = harvest_resp.json()["id"]

    # Delete bed
    await client.delete(f"/api/beds/{bed_id}", headers=auth_header(token))

    # Harvest should still exist with bed=null
    resp = await client.get(f"/api/harvests/{harvest_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["bed"] is None
    assert resp.json()["bed_id"] is None


async def test_watering_with_deleted_bed_keeps_null(client: AsyncClient, admin_user):
    _, token = admin_user

    garden_resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Test"}
    )
    bed_resp = await client.post(
        "/api/beds/", headers=auth_header(token),
        json={"garden_id": garden_resp.json()["id"], "name": "Beet 1"},
    )
    bed_id = bed_resp.json()["id"]

    event_resp = await client.post(
        "/api/watering/", headers=auth_header(token),
        json={"bed_id": bed_id, "started_at": "2026-07-15T08:00:00Z"},
    )
    event_id = event_resp.json()["id"]

    await client.delete(f"/api/beds/{bed_id}", headers=auth_header(token))

    resp = await client.get(f"/api/watering/{event_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["bed"] is None


async def test_harvest_with_deleted_plant_keeps_null(client: AsyncClient, admin_user):
    _, token = admin_user

    plant_resp = await client.post(
        "/api/plants/", headers=auth_header(token), json={"name": "Tomate"}
    )
    plant_id = plant_resp.json()["id"]

    harvest_resp = await client.post(
        "/api/harvests/", headers=auth_header(token),
        json={"plant_id": plant_id, "amount": 1, "unit": "kg", "harvest_date": "2026-07-15"},
    )
    harvest_id = harvest_resp.json()["id"]

    await client.delete(f"/api/plants/{plant_id}", headers=auth_header(token))

    resp = await client.get(f"/api/harvests/{harvest_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["plant"] is None


# ═══════════════════════════════════════════════════════════════════
# Auth Edge Cases
# ═══════════════════════════════════════════════════════════════════

async def test_expired_token_rejected(client: AsyncClient):
    """Completely invalid token should be rejected."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer totally-invalid-token"},
    )
    assert response.status_code == 401


async def test_missing_bearer_prefix_rejected(client: AsyncClient):
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "NotBearer some-token"},
    )
    assert response.status_code == 401


async def test_empty_auth_header_rejected(client: AsyncClient):
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": ""},
    )
    assert response.status_code == 401


async def test_deactivated_user_token_rejected(client: AsyncClient, admin_user, normal_user):
    """A deactivated user's token should be rejected."""
    _, admin_token = admin_user
    user, user_token = normal_user

    # Deactivate user
    await client.patch(
        f"/api/users/{user.id}",
        headers=auth_header(admin_token),
        json={"is_active": False},
    )

    # User's existing token should now fail
    resp = await client.get("/api/auth/me", headers=auth_header(user_token))
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# Validation Edge Cases
# ═══════════════════════════════════════════════════════════════════

async def test_garden_name_too_long(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/gardens/",
        headers=auth_header(token),
        json={"name": "x" * 101},
    )
    assert response.status_code == 422


async def test_plant_season_month_zero(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/plants/",
        headers=auth_header(token),
        json={"name": "Test", "growing_season_start": 0},
    )
    assert response.status_code == 422


async def test_harvest_negative_amount(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/harvests/",
        headers=auth_header(token),
        json={"amount": -1, "unit": "kg", "harvest_date": "2026-07-15"},
    )
    assert response.status_code == 422


async def test_watering_negative_duration(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z", "duration_minutes": -5},
    )
    assert response.status_code == 422


async def test_watering_soil_moisture_over_100(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/watering/",
        headers=auth_header(token),
        json={"started_at": "2026-07-15T08:00:00Z", "soil_moisture_before": 150},
    )
    assert response.status_code == 422


async def test_bed_negative_area(client: AsyncClient, admin_user):
    _, token = admin_user
    garden_resp = await client.post(
        "/api/gardens/", headers=auth_header(token), json={"name": "Test"}
    )
    response = await client.post(
        "/api/beds/",
        headers=auth_header(token),
        json={"garden_id": garden_resp.json()["id"], "name": "Bad", "area_sqm": -5},
    )
    assert response.status_code == 422


async def test_fertilizing_empty_type(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/fertilizing/",
        headers=auth_header(token),
        json={"fertilizer_type": "", "event_date": "2026-04-10"},
    )
    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════
# Multiple Users See Same Data
# ═══════════════════════════════════════════════════════════════════

async def test_both_users_see_same_gardens(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    _, user_token = normal_user

    await client.post(
        "/api/gardens/", headers=auth_header(admin_token), json={"name": "Shared Garden"}
    )

    admin_resp = await client.get("/api/gardens/", headers=auth_header(admin_token))
    user_resp = await client.get("/api/gardens/", headers=auth_header(user_token))

    assert len(admin_resp.json()) == len(user_resp.json())
    assert admin_resp.json()[0]["name"] == "Shared Garden"
    assert user_resp.json()[0]["name"] == "Shared Garden"


async def test_harvest_shows_correct_user(client: AsyncClient, admin_user, normal_user):
    """Each user's harvest should show their own name."""
    _, admin_token = admin_user
    _, user_token = normal_user

    await client.post(
        "/api/harvests/", headers=auth_header(admin_token),
        json={"amount": 1, "unit": "kg", "harvest_date": "2026-07-15"},
    )
    await client.post(
        "/api/harvests/", headers=auth_header(user_token),
        json={"amount": 2, "unit": "kg", "harvest_date": "2026-07-15"},
    )

    resp = await client.get("/api/harvests/", headers=auth_header(admin_token))
    harvests = resp.json()
    assert len(harvests) == 2

    users = {h["user"]["display_name"] for h in harvests}
    assert "Test Admin" in users
    assert "Test User" in users


async def test_filter_harvests_by_user(client: AsyncClient, admin_user, normal_user):
    user, admin_token = admin_user
    normal, user_token = normal_user

    await client.post(
        "/api/harvests/", headers=auth_header(admin_token),
        json={"amount": 1, "unit": "kg", "harvest_date": "2026-07-15"},
    )
    await client.post(
        "/api/harvests/", headers=auth_header(user_token),
        json={"amount": 2, "unit": "kg", "harvest_date": "2026-07-15"},
    )

    resp = await client.get(
        "/api/harvests/", headers=auth_header(admin_token),
        params={"user_id": normal.id},
    )
    assert len(resp.json()) == 1
    assert resp.json()[0]["user"]["display_name"] == "Test User"

