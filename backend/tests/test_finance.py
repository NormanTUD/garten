from httpx import AsyncClient

from tests.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════
# Categories
# ═══════════════════════════════════════════════════════════════════

async def test_create_category(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/categories/", headers=auth_header(token),
        json={"name": "Saatgut", "icon": "🌱"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Saatgut"


async def test_create_category_duplicate(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post("/api/finance/categories/", headers=auth_header(token), json={"name": "Erde"})
    resp = await client.post("/api/finance/categories/", headers=auth_header(token), json={"name": "Erde"})
    assert resp.status_code == 409


async def test_list_categories(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post("/api/finance/categories/", headers=auth_header(token), json={"name": "A"})
    await client.post("/api/finance/categories/", headers=auth_header(token), json={"name": "B"})
    resp = await client.get("/api/finance/categories/", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ═══════════════════════════════════════════════════════════════════
# Recurring Costs
# ═══════════════════════════════════════════════════════════════════

async def test_create_recurring_cost(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/recurring/", headers=auth_header(token),
        json={"description": "Pacht", "amount_cents": 5000, "interval": "monthly"},
    )
    assert resp.status_code == 201
    assert resp.json()["amount_cents"] == 5000
    assert resp.json()["interval"] == "monthly"


async def test_create_recurring_cost_yearly(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/recurring/", headers=auth_header(token),
        json={"description": "Versicherung", "amount_cents": 12000, "interval": "yearly"},
    )
    assert resp.status_code == 201


async def test_create_recurring_cost_normal_user_forbidden(client: AsyncClient, normal_user):
    _, token = normal_user
    resp = await client.post(
        "/api/finance/recurring/", headers=auth_header(token),
        json={"description": "Nope", "amount_cents": 100, "interval": "monthly"},
    )
    assert resp.status_code == 403


async def test_update_recurring_cost(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/recurring/", headers=auth_header(token),
        json={"description": "Wasser", "amount_cents": 3000, "interval": "monthly"},
    )
    cost_id = resp.json()["id"]
    resp2 = await client.patch(
        f"/api/finance/recurring/{cost_id}", headers=auth_header(token),
        json={"amount_cents": 3500},
    )
    assert resp2.status_code == 200
    assert resp2.json()["amount_cents"] == 3500


async def test_delete_recurring_cost(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/recurring/", headers=auth_header(token),
        json={"description": "Temp", "amount_cents": 100, "interval": "monthly"},
    )
    cost_id = resp.json()["id"]
    del_resp = await client.delete(f"/api/finance/recurring/{cost_id}", headers=auth_header(token))
    assert del_resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════
# Garden Expenses
# ═══════════════════════════════════════════════════════════════════

async def test_create_expense(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 2500, "description": "Erde 20L", "expense_date": "2026-04-10"},
    )
    assert resp.status_code == 201
    assert resp.json()["amount_cents"] == 2500
    assert resp.json()["user"]["display_name"] == "Test Admin"


async def test_create_expense_with_dynamic_category(client: AsyncClient, admin_user):
    """category_name creates category on the fly if it doesn't exist."""
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={
            "amount_cents": 1500,
            "description": "Tomatensamen",
            "expense_date": "2026-03-01",
            "category_name": "Saatgut",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["category"]["name"] == "Saatgut"

    # Second expense with same category_name should reuse
    resp2 = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={
            "amount_cents": 800,
            "description": "Gurkensamen",
            "expense_date": "2026-03-01",
            "category_name": "Saatgut",
        },
    )
    assert resp2.status_code == 201
    assert resp2.json()["category"]["id"] == resp.json()["category"]["id"]


async def test_create_expense_zero_amount(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 0, "description": "Free", "expense_date": "2026-04-10"},
    )
    assert resp.status_code == 422


async def test_list_expenses(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post("/api/finance/expenses/", headers=auth_header(token),
                      json={"amount_cents": 100, "description": "A", "expense_date": "2026-04-10"})
    await client.post("/api/finance/expenses/", headers=auth_header(token),
                      json={"amount_cents": 200, "description": "B", "expense_date": "2026-04-15"})
    resp = await client.get("/api/finance/expenses/", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_delete_expense(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post("/api/finance/expenses/", headers=auth_header(token),
                             json={"amount_cents": 100, "description": "Del", "expense_date": "2026-04-10"})
    expense_id = resp.json()["id"]
    del_resp = await client.delete(f"/api/finance/expenses/{expense_id}", headers=auth_header(token))
    assert del_resp.status_code == 204


async def test_normal_user_can_create_expense(client: AsyncClient, normal_user):
    _, token = normal_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 500, "description": "Blumenerde", "expense_date": "2026-04-10"},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["display_name"] == "Test User"


# ═══════════════════════════════════════════════════════════════════
# Member Payments
# ═══════════════════════════════════════════════════════════════════

async def test_create_payment_cash(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(token),
        json={"amount_cents": 5000, "payment_type": "cash", "payment_date": "2026-04-15"},
    )
    assert resp.status_code == 201
    assert resp.json()["payment_type"] == "cash"
    assert resp.json()["confirmed_by_admin"] is False


async def test_create_payment_material(client: AsyncClient, normal_user):
    _, token = normal_user
    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(token),
        json={
            "amount_cents": 2000,
            "payment_type": "material",
            "description": "Erde mitgebracht",
            "payment_date": "2026-04-10",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["payment_type"] == "material"


async def test_create_payment_invalid_type(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(token),
        json={"amount_cents": 100, "payment_type": "bitcoin", "payment_date": "2026-04-10"},
    )
    assert resp.status_code == 422


async def test_admin_confirms_payment(client: AsyncClient, admin_user, normal_user):
    _, user_token = normal_user
    _, admin_token = admin_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(user_token),
        json={"amount_cents": 3000, "payment_type": "cash", "payment_date": "2026-04-15"},
    )
    payment_id = resp.json()["id"]
    assert resp.json()["confirmed_by_admin"] is False

    confirm_resp = await client.patch(
        f"/api/finance/payments/{payment_id}", headers=auth_header(admin_token),
        json={"confirmed_by_admin": True},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["confirmed_by_admin"] is True


async def test_normal_user_cannot_confirm_payment(client: AsyncClient, admin_user, normal_user):
    _, user_token = normal_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(user_token),
        json={"amount_cents": 1000, "payment_type": "cash", "payment_date": "2026-04-15"},
    )
    payment_id = resp.json()["id"]

    confirm_resp = await client.patch(
        f"/api/finance/payments/{payment_id}", headers=auth_header(user_token),
        json={"confirmed_by_admin": True},
    )
    assert confirm_resp.status_code == 403


async def test_list_payments(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    _, user_token = normal_user

    await client.post("/api/finance/payments/", headers=auth_header(admin_token),
                      json={"amount_cents": 5000, "payment_type": "cash", "payment_date": "2026-04-10"})
    await client.post("/api/finance/payments/", headers=auth_header(user_token),
                      json={"amount_cents": 3000, "payment_type": "transfer", "payment_date": "2026-04-15"})

    resp = await client.get("/api/finance/payments/", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_payments_filter_by_user(client: AsyncClient, admin_user, normal_user):
    admin, admin_token = admin_user
    _, user_token = normal_user

    await client.post("/api/finance/payments/", headers=auth_header(admin_token),
                      json={"amount_cents": 5000, "payment_type": "cash", "payment_date": "2026-04-10"})
    await client.post("/api/finance/payments/", headers=auth_header(user_token),
                      json={"amount_cents": 3000, "payment_type": "cash", "payment_date": "2026-04-15"})

    resp = await client.get("/api/finance/payments/", headers=auth_header(admin_token),
                            params={"user_id": admin.id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_delete_payment(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post("/api/finance/payments/", headers=auth_header(token),
                             json={"amount_cents": 1000, "payment_type": "cash", "payment_date": "2026-04-10"})
    payment_id = resp.json()["id"]
    del_resp = await client.delete(f"/api/finance/payments/{payment_id}", headers=auth_header(token))
    assert del_resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════
# Fund Overview / Balance
# ═══════════════════════════════════════════════════════════════════

async def test_fund_overview_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/finance/fund/", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recurring_monthly_cents"] == 0
    assert data["total_recurring_yearly_cents"] == 0
    assert data["total_onetime_expenses_cents"] == 0
    assert data["total_costs_annual_cents"] == 0
    assert data["member_count"] >= 1


async def test_fund_overview_with_recurring(client: AsyncClient, admin_user):
    _, token = admin_user

    # Add recurring costs
    await client.post("/api/finance/recurring/", headers=auth_header(token),
                      json={"description": "Pacht", "amount_cents": 5000, "interval": "monthly"})
    await client.post("/api/finance/recurring/", headers=auth_header(token),
                      json={"description": "Versicherung", "amount_cents": 12000, "interval": "yearly"})

    resp = await client.get("/api/finance/fund/", headers=auth_header(token))
    data = resp.json()
    assert data["total_recurring_monthly_cents"] == 5000
    assert data["total_recurring_yearly_cents"] == 12000
    assert data["total_recurring_annual_cents"] == (5000 * 12) + 12000  # 72000


async def test_fund_overview_with_expenses_and_payments(client: AsyncClient, admin_user, normal_user):
    """Full scenario: recurring costs + one-time expense + payments."""
    admin, admin_token = admin_user
    user, user_token = normal_user

    # Recurring: 5000/month = 60000/year
    await client.post("/api/finance/recurring/", headers=auth_header(admin_token),
                      json={"description": "Pacht", "amount_cents": 5000, "interval": "monthly"})

    # One-time expense: 2000
    await client.post("/api/finance/expenses/", headers=auth_header(admin_token),
                      json={"amount_cents": 2000, "description": "Erde", "expense_date": "2026-04-10"})

    # Total annual costs: 60000 + 2000 = 62000
    # 2 members → 31000 per person

    # Admin pays 20000
    await client.post("/api/finance/payments/", headers=auth_header(admin_token),
                      json={"amount_cents": 20000, "payment_type": "cash", "payment_date": "2026-04-15"})

    # User pays 10000
    await client.post("/api/finance/payments/", headers=auth_header(user_token),
                      json={"amount_cents": 10000, "payment_type": "transfer", "payment_date": "2026-04-15"})

    resp = await client.get("/api/finance/fund/", headers=auth_header(admin_token))
    data = resp.json()

    assert data["total_costs_annual_cents"] == 62000
    assert data["member_count"] == 2
    assert data["share_per_member_annual_cents"] == 31000
    assert data["total_payments_cents"] == 30000

    # Check per-member balances
    admin_balance = next(b for b in data["member_balances"] if b["user_id"] == admin.id)
    user_balance = next(b for b in data["member_balances"] if b["user_id"] == user.id)

    assert admin_balance["total_paid_cents"] == 20000
    assert admin_balance["share_cents"] == 31000
    assert admin_balance["remaining_cents"] == 11000  # Still owes 11000

    assert user_balance["total_paid_cents"] == 10000
    assert user_balance["share_cents"] == 31000
    assert user_balance["remaining_cents"] == 21000  # Still owes 21000


async def test_fund_overview_by_year(client: AsyncClient, admin_user):
    _, token = admin_user

    await client.post("/api/finance/recurring/", headers=auth_header(token),
                      json={"description": "Pacht", "amount_cents": 5000, "interval": "monthly"})

    # Expense in 2025
    await client.post("/api/finance/expenses/", headers=auth_header(token),
                      json={"amount_cents": 1000, "description": "Alt", "expense_date": "2025-06-01"})

    # Expense in 2026
    await client.post("/api/finance/expenses/", headers=auth_header(token),
                      json={"amount_cents": 2000, "description": "Neu", "expense_date": "2026-04-10"})

    # Query 2026 only
    resp = await client.get("/api/finance/fund/", headers=auth_header(token), params={"year": 2026})
    data = resp.json()
    assert data["total_onetime_expenses_cents"] == 2000

    # Query 2025
    resp2 = await client.get("/api/finance/fund/", headers=auth_header(token), params={"year": 2025})
    data2 = resp2.json()
    assert data2["total_onetime_expenses_cents"] == 1000


async def test_fund_overview_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/finance/fund/")
    assert resp.status_code == 401

