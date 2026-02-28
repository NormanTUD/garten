import pytest
from httpx import AsyncClient


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
async def shopping_item(user_client: AsyncClient):
    """Create a shopping item as normal user."""
    resp = await user_client.post("/api/shopping/", json={
        "title": "Blumenerde",
        "quantity": "3 Säcke",
        "category": "Erde & Substrate",
        "notes": "40L pro Sack",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def purchased_item(user_client: AsyncClient, admin_client: AsyncClient):
    """Create and purchase a shopping item."""
    resp = await user_client.post("/api/shopping/", json={
        "title": "Tomatensamen",
        "quantity": "2 Packungen",
        "category": "Samen & Pflanzen",
    })
    assert resp.status_code == 201
    item = resp.json()

    resp = await user_client.post(f"/api/shopping/{item['id']}/purchase", json={
        "cost_cents": 599,
        "notes": "Baumarkt",
    })
    assert resp.status_code == 200
    return resp.json()


# ─── CRUD Tests ────────────────────────────────────────────

class TestShoppingCRUD:
    async def test_create_item(self, shopping_item: dict):
        assert shopping_item["title"] == "Blumenerde"
        assert shopping_item["quantity"] == "3 Säcke"
        assert shopping_item["category"] == "Erde & Substrate"
        assert shopping_item["notes"] == "40L pro Sack"
        assert shopping_item["purchased"] is False
        assert shopping_item["cost_cents"] is None
        assert shopping_item["expense_id"] is None

    async def test_create_item_minimal(self, user_client: AsyncClient):
        resp = await user_client.post("/api/shopping/", json={
            "title": "Gießkanne",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Gießkanne"
        assert data["quantity"] is None
        assert data["category"] is None
        assert data["notes"] is None

    async def test_create_item_empty_title(self, user_client: AsyncClient):
        resp = await user_client.post("/api/shopping/", json={
            "title": "",
        })
        assert resp.status_code == 422

    async def test_create_item_no_title(self, user_client: AsyncClient):
        resp = await user_client.post("/api/shopping/", json={
            "quantity": "5 Stück",
        })
        assert resp.status_code == 422

    async def test_list_items_open_only(self, user_client: AsyncClient, shopping_item: dict):
        resp = await user_client.get("/api/shopping/")
        assert resp.status_code == 200
        items = resp.json()
        assert any(i["id"] == shopping_item["id"] for i in items)
        # All should be unpurchased
        for item in items:
            assert item["purchased"] is False

    async def test_list_items_include_purchased(
        self, user_client: AsyncClient, shopping_item: dict, purchased_item: dict
    ):
        resp = await user_client.get("/api/shopping/", params={"include_purchased": True})
        assert resp.status_code == 200
        items = resp.json()
        ids = [i["id"] for i in items]
        assert shopping_item["id"] in ids
        assert purchased_item["id"] in ids

    async def test_purchased_not_in_default_list(
        self, user_client: AsyncClient, purchased_item: dict
    ):
        resp = await user_client.get("/api/shopping/")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()]
        assert purchased_item["id"] not in ids

    async def test_update_item(self, user_client: AsyncClient, shopping_item: dict):
        resp = await user_client.put(f"/api/shopping/{shopping_item['id']}", json={
            "title": "Bio-Blumenerde",
            "quantity": "5 Säcke",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Bio-Blumenerde"
        assert data["quantity"] == "5 Säcke"

    async def test_update_item_not_found(self, user_client: AsyncClient):
        resp = await user_client.put("/api/shopping/99999", json={
            "title": "Nope",
        })
        assert resp.status_code == 404

    async def test_delete_item(self, user_client: AsyncClient, shopping_item: dict):
        resp = await user_client.delete(f"/api/shopping/{shopping_item['id']}")
        assert resp.status_code == 204

        # Verify gone
        resp = await user_client.get("/api/shopping/", params={"include_purchased": True})
        ids = [i["id"] for i in resp.json()]
        assert shopping_item["id"] not in ids

    async def test_delete_item_not_found(self, user_client: AsyncClient):
        resp = await user_client.delete("/api/shopping/99999")
        assert resp.status_code == 404


# ─── Purchase Tests ────────────────────────────────────────

class TestShoppingPurchase:
    async def test_purchase_item(self, purchased_item: dict):
        assert purchased_item["purchased"] is True
        assert purchased_item["cost_cents"] == 599
        assert purchased_item["purchased_by_name"] is not None
        assert purchased_item["purchased_at"] is not None
        assert purchased_item["expense_id"] is not None

    async def test_purchase_creates_expense(self, user_client: AsyncClient, purchased_item: dict):
        """Purchasing should create a finance entry."""
        assert purchased_item["expense_id"] is not None

    async def test_purchase_invalid_cost(self, user_client: AsyncClient, shopping_item: dict):
        resp = await user_client.post(f"/api/shopping/{shopping_item['id']}/purchase", json={
            "cost_cents": 0,
        })
        assert resp.status_code == 422

    async def test_purchase_negative_cost(self, user_client: AsyncClient, shopping_item: dict):
        resp = await user_client.post(f"/api/shopping/{shopping_item['id']}/purchase", json={
            "cost_cents": -100,
        })
        assert resp.status_code == 422

    async def test_purchase_already_purchased(self, user_client: AsyncClient, purchased_item: dict):
        resp = await user_client.post(f"/api/shopping/{purchased_item['id']}/purchase", json={
            "cost_cents": 1000,
        })
        assert resp.status_code == 404

    async def test_purchase_not_found(self, user_client: AsyncClient):
        resp = await user_client.post("/api/shopping/99999/purchase", json={
            "cost_cents": 500,
        })
        assert resp.status_code == 404

    async def test_purchase_with_notes(self, user_client: AsyncClient):
        # Create item
        resp = await user_client.post("/api/shopping/", json={
            "title": "Rasendünger",
        })
        item = resp.json()

        # Purchase with notes
        resp = await user_client.post(f"/api/shopping/{item['id']}/purchase", json={
            "cost_cents": 1299,
            "notes": "OBI Filiale Mitte",
        })
        assert resp.status_code == 200
        assert resp.json()["cost_cents"] == 1299


# ─── Unpurchase Tests ──────────────────────────────────────

class TestShoppingUnpurchase:
    async def test_unpurchase_item(self, admin_client: AsyncClient, purchased_item: dict):
        expense_id = purchased_item["expense_id"]

        resp = await admin_client.post(f"/api/shopping/{purchased_item['id']}/unpurchase")
        assert resp.status_code == 200
        data = resp.json()
        assert data["purchased"] is False
        assert data["cost_cents"] is None
        assert data["purchased_by_name"] is None
        assert data["expense_id"] is None

    async def test_unpurchase_not_purchased(self, admin_client: AsyncClient, shopping_item: dict):
        resp = await admin_client.post(f"/api/shopping/{shopping_item['id']}/unpurchase")
        assert resp.status_code == 404

    async def test_unpurchase_not_found(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/shopping/99999/unpurchase")
        assert resp.status_code == 404

    async def test_user_cannot_unpurchase(self, user_client: AsyncClient, purchased_item: dict):
        resp = await user_client.post(f"/api/shopping/{purchased_item['id']}/unpurchase")
        assert resp.status_code == 403


# ─── Delete Purchased Item Tests ───────────────────────────

class TestShoppingDeletePurchased:
    async def test_delete_purchased_item_removes_expense(
        self, user_client: AsyncClient,
    ):
        """Deleting a purchased item should also delete the finance entry."""
        # Create and purchase
        resp = await user_client.post("/api/shopping/", json={
            "title": "Schlauch",
        })
        item = resp.json()

        await user_client.post(f"/api/shopping/{item['id']}/purchase", json={
            "cost_cents": 2499,
        })

        # Delete
        resp = await user_client.delete(f"/api/shopping/{item['id']}")
        assert resp.status_code == 204


# ─── Auth Tests ────────────────────────────────────────────

class TestShoppingAuth:
    async def test_unauthenticated_cannot_list(self, client: AsyncClient):
        resp = await client.get("/api/shopping/")
        assert resp.status_code == 401

    async def test_unauthenticated_cannot_create(self, client: AsyncClient):
        resp = await client.post("/api/shopping/", json={
            "title": "Test",
        })
        assert resp.status_code == 401

    async def test_user_can_create(self, user_client: AsyncClient):
        resp = await user_client.post("/api/shopping/", json={
            "title": "Harke",
        })
        assert resp.status_code == 201

    async def test_admin_can_create(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/shopping/", json={
            "title": "Spaten",
        })
        assert resp.status_code == 201

    async def test_user_can_purchase(self, user_client: AsyncClient):
        resp = await user_client.post("/api/shopping/", json={
            "title": "Handschuhe",
        })
        item = resp.json()

        resp = await user_client.post(f"/api/shopping/{item['id']}/purchase", json={
            "cost_cents": 899,
        })
        assert resp.status_code == 200

