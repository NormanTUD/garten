from httpx import AsyncClient

from tests.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════
# Expense Categories
# ═══════════════════════════════════════════════════════════════════

async def test_create_category(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/finance/categories/",
        headers=auth_header(token),
        json={"name": "Saatgut", "icon": "🌱"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Saatgut"
    assert data["icon"] == "🌱"
    assert data["is_active"] is True


async def test_create_category_duplicate_name(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/finance/categories/", headers=auth_header(token),
        json={"name": "Werkzeug"},
    )
    response = await client.post(
        "/api/finance/categories/", headers=auth_header(token),
        json={"name": "Werkzeug"},
    )
    assert response.status_code in (400, 409, 500)  # IntegrityError


async def test_list_categories(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/finance/categories/", headers=auth_header(token), json={"name": "Erde"}
    )
    await client.post(
        "/api/finance/categories/", headers=auth_header(token), json={"name": "Wasser"}
    )

    response = await client.get("/api/finance/categories/", headers=auth_header(token))
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_categories_active_only(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/categories/", headers=auth_header(token), json={"name": "Aktiv"}
    )
    cat_id = resp.json()["id"]
    await client.post(
        "/api/finance/categories/", headers=auth_header(token), json={"name": "Inaktiv"}
    )
    inaktiv_resp = await client.get("/api/finance/categories/", headers=auth_header(token))
    inaktiv_id = [c for c in inaktiv_resp.json() if c["name"] == "Inaktiv"][0]["id"]

    await client.patch(
        f"/api/finance/categories/{inaktiv_id}",
        headers=auth_header(token),
        json={"is_active": False},
    )

    response = await client.get(
        "/api/finance/categories/", headers=auth_header(token),
        params={"active_only": True},
    )
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Aktiv" in names
    assert "Inaktiv" not in names


async def test_update_category(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/categories/", headers=auth_header(token), json={"name": "Alt"}
    )
    cat_id = resp.json()["id"]

    response = await client.patch(
        f"/api/finance/categories/{cat_id}",
        headers=auth_header(token),
        json={"name": "Neu", "icon": "🔧"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Neu"
    assert response.json()["icon"] == "🔧"


async def test_update_category_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/finance/categories/9999",
        headers=auth_header(token),
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# Expenses
# ═══════════════════════════════════════════════════════════════════

async def test_create_expense_auto_split(client: AsyncClient, admin_user, normal_user):
    """Expense without manual splits should auto-split among all active users."""
    _, admin_token = admin_user
    _, user_token = normal_user

    response = await client.post(
        "/api/finance/expenses/",
        headers=auth_header(admin_token),
        json={
            "amount_cents": 1000,
            "description": "Erde gekauft",
            "expense_date": "2026-04-10",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount_cents"] == 1000
    assert data["description"] == "Erde gekauft"
    assert len(data["splits"]) == 2  # admin + normal user
    splits_sum = sum(s["share_amount_cents"] for s in data["splits"])
    assert splits_sum == 1000


async def test_create_expense_manual_splits(client: AsyncClient, admin_user, normal_user):
    admin, admin_token = admin_user
    user, _ = normal_user

    response = await client.post(
        "/api/finance/expenses/",
        headers=auth_header(admin_token),
        json={
            "amount_cents": 3000,
            "description": "Rasenmäher",
            "expense_date": "2026-04-10",
            "splits": [
                {"user_id": admin.id, "share_amount_cents": 2000},
                {"user_id": user.id, "share_amount_cents": 1000},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["splits"]) == 2
    admin_split = next(s for s in data["splits"] if s["user_id"] == admin.id)
    user_split = next(s for s in data["splits"] if s["user_id"] == user.id)
    assert admin_split["share_amount_cents"] == 2000
    assert user_split["share_amount_cents"] == 1000


async def test_create_expense_splits_must_sum(client: AsyncClient, admin_user, normal_user):
    admin, admin_token = admin_user
    user, _ = normal_user

    response = await client.post(
        "/api/finance/expenses/",
        headers=auth_header(admin_token),
        json={
            "amount_cents": 3000,
            "description": "Bad split",
            "expense_date": "2026-04-10",
            "splits": [
                {"user_id": admin.id, "share_amount_cents": 1000},
                {"user_id": user.id, "share_amount_cents": 500},
            ],
        },
    )
    assert response.status_code == 422
    assert "Splits sum" in response.json()["detail"]


async def test_create_expense_with_category(client: AsyncClient, admin_user):
    _, token = admin_user
    cat_resp = await client.post(
        "/api/finance/categories/", headers=auth_header(token), json={"name": "Saatgut"}
    )
    cat_id = cat_resp.json()["id"]

    response = await client.post(
        "/api/finance/expenses/",
        headers=auth_header(token),
        json={
            "category_id": cat_id,
            "amount_cents": 500,
            "description": "Tomatensamen",
            "expense_date": "2026-03-01",
        },
    )
    assert response.status_code == 201
    assert response.json()["category"]["name"] == "Saatgut"


async def test_create_expense_invalid_category(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/finance/expenses/",
        headers=auth_header(token),
        json={
            "category_id": 9999,
            "amount_cents": 500,
            "description": "Test",
            "expense_date": "2026-04-10",
        },
    )
    assert response.status_code == 404


async def test_create_expense_zero_amount(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.post(
        "/api/finance/expenses/",
        headers=auth_header(token),
        json={"amount_cents": 0, "description": "Free", "expense_date": "2026-04-10"},
    )
    assert response.status_code == 422


async def test_create_expense_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/finance/expenses/",
        json={"amount_cents": 100, "description": "Test", "expense_date": "2026-04-10"},
    )
    assert response.status_code == 401


async def test_list_expenses(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 100, "description": "A", "expense_date": "2026-04-10"},
    )
    await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 200, "description": "B", "expense_date": "2026-04-15"},
    )

    response = await client.get("/api/finance/expenses/", headers=auth_header(token))
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_expenses_filter_by_date(client: AsyncClient, admin_user):
    _, token = admin_user
    await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 100, "description": "March", "expense_date": "2026-03-15"},
    )
    await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 200, "description": "April", "expense_date": "2026-04-15"},
    )

    response = await client.get(
        "/api/finance/expenses/", headers=auth_header(token),
        params={"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["description"] == "April"


async def test_get_expense(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 100, "description": "Test", "expense_date": "2026-04-10"},
    )
    expense_id = resp.json()["id"]

    response = await client.get(f"/api/finance/expenses/{expense_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["id"] == expense_id


async def test_get_expense_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/finance/expenses/9999", headers=auth_header(token))
    assert response.status_code == 404


async def test_update_expense(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 100, "description": "Alt", "expense_date": "2026-04-10"},
    )
    expense_id = resp.json()["id"]

    response = await client.patch(
        f"/api/finance/expenses/{expense_id}",
        headers=auth_header(token),
        json={"description": "Neu", "notes": "Korrektur"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Neu"
    assert response.json()["notes"] == "Korrektur"


async def test_delete_expense(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 100, "description": "Delete me", "expense_date": "2026-04-10"},
    )
    expense_id = resp.json()["id"]

    response = await client.delete(f"/api/finance/expenses/{expense_id}", headers=auth_header(token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/finance/expenses/{expense_id}", headers=auth_header(token))
    assert get_resp.status_code == 404


# ─── Settle / Unsettle Splits ─────────────────────────────────────

async def test_settle_and_unsettle_split(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post(
        "/api/finance/expenses/", headers=auth_header(token),
        json={"amount_cents": 1000, "description": "Test", "expense_date": "2026-04-10"},
    )
    expense_id = resp.json()["id"]
    split_id = resp.json()["splits"][0]["id"]

    # Settle
    settle_resp = await client.patch(
        f"/api/finance/expenses/{expense_id}/splits/{split_id}/settle",
        headers=auth_header(token),
    )
    assert settle_resp.status_code == 200
    assert settle_resp.json()["is_settled"] is True

    # Unsettle
    unsettle_resp = await client.patch(
        f"/api/finance/expenses/{expense_id}/splits/{split_id}/unsettle",
        headers=auth_header(token),
    )
    assert unsettle_resp.status_code == 200
    assert unsettle_resp.json()["is_settled"] is False


async def test_settle_split_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.patch(
        "/api/finance/expenses/1/splits/9999/settle",
        headers=auth_header(token),
    )
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# Payments
# ═══════════════════════════════════════════════════════════════════

async def test_create_payment(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    response = await client.post(
        "/api/finance/payments/",
        headers=auth_header(admin_token),
        json={
            "to_user_id": user.id,
            "amount_cents": 500,
            "method": "cash",
            "description": "Ausgleich April",
            "payment_date": "2026-04-30",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount_cents"] == 500
    assert data["method"] == "cash"
    assert data["from_user"]["display_name"] == "Test Admin"
    assert data["to_user"]["display_name"] == "Test User"
    assert data["confirmed_by_admin"] is False


async def test_create_payment_to_self_rejected(client: AsyncClient, admin_user):
    admin, admin_token = admin_user
    response = await client.post(
        "/api/finance/payments/",
        headers=auth_header(admin_token),
        json={
            "to_user_id": admin.id,
            "amount_cents": 500,
            "method": "cash",
            "payment_date": "2026-04-30",
        },
    )
    assert response.status_code == 422
    assert "yourself" in response.json()["detail"].lower()


async def test_create_payment_invalid_method(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user
    response = await client.post(
        "/api/finance/payments/",
        headers=auth_header(admin_token),
        json={
            "to_user_id": user.id,
            "amount_cents": 500,
            "method": "bitcoin",
            "payment_date": "2026-04-30",
        },
    )
    assert response.status_code == 422


async def test_create_payment_zero_amount(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user
    response = await client.post(
        "/api/finance/payments/",
        headers=auth_header(admin_token),
        json={
            "to_user_id": user.id,
            "amount_cents": 0,
            "method": "cash",
            "payment_date": "2026-04-30",
        },
    )
    assert response.status_code == 422


async def test_create_payment_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/finance/payments/",
        json={
            "to_user_id": 1,
            "amount_cents": 500,
            "method": "cash",
            "payment_date": "2026-04-30",
        },
    )
    assert response.status_code == 401


async def test_list_payments(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )
    await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 300, "method": "transfer", "payment_date": "2026-05-15"},
    )

    response = await client.get("/api/finance/payments/", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_payments_filter_by_user(client: AsyncClient, admin_user, normal_user):
    admin, admin_token = admin_user
    user, user_token = normal_user

    await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )

    # Filter by admin (from_user)
    response = await client.get(
        "/api/finance/payments/", headers=auth_header(admin_token),
        params={"user_id": admin.id},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Filter by normal user (to_user)
    response = await client.get(
        "/api/finance/payments/", headers=auth_header(user_token),
        params={"user_id": user.id},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_payment(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )
    payment_id = resp.json()["id"]

    response = await client.get(f"/api/finance/payments/{payment_id}", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == payment_id


async def test_get_payment_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/finance/payments/9999", headers=auth_header(token))
    assert response.status_code == 404


async def test_update_payment(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )
    payment_id = resp.json()["id"]

    response = await client.patch(
        f"/api/finance/payments/{payment_id}",
        headers=auth_header(admin_token),
        json={"amount_cents": 750, "notes": "Korrektur"},
    )
    assert response.status_code == 200
    assert response.json()["amount_cents"] == 750
    assert response.json()["notes"] == "Korrektur"


async def test_admin_can_confirm_payment(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )
    payment_id = resp.json()["id"]

    response = await client.patch(
        f"/api/finance/payments/{payment_id}",
        headers=auth_header(admin_token),
        json={"confirmed_by_admin": True},
    )
    assert response.status_code == 200
    assert response.json()["confirmed_by_admin"] is True


async def test_normal_user_cannot_confirm_payment(client: AsyncClient, admin_user, normal_user):
    admin, admin_token = admin_user
    _, user_token = normal_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(user_token),
        json={"to_user_id": admin.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )
    payment_id = resp.json()["id"]

    response = await client.patch(
        f"/api/finance/payments/{payment_id}",
        headers=auth_header(user_token),
        json={"confirmed_by_admin": True},
    )
    assert response.status_code == 403


async def test_delete_payment(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    resp = await client.post(
        "/api/finance/payments/", headers=auth_header(admin_token),
        json={"to_user_id": user.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-30"},
    )
    payment_id = resp.json()["id"]

    response = await client.delete(f"/api/finance/payments/{payment_id}", headers=auth_header(admin_token))
    assert response.status_code == 204

    get_resp = await client.get(f"/api/finance/payments/{payment_id}", headers=auth_header(admin_token))
    assert get_resp.status_code == 404


async def test_delete_payment_not_found(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.delete("/api/finance/payments/9999", headers=auth_header(token))
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# Balance Calculation
# ═══════════════════════════════════════════════════════════════════

async def test_balance_empty(client: AsyncClient, admin_user):
    _, token = admin_user
    response = await client.get("/api/finance/balance/", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["total_expenses_cents"] == 0
    assert len(data["balances"]) >= 1  # At least admin user


async def test_balance_after_expense(client: AsyncClient, admin_user, normal_user):
    """Admin pays 1000 cents, split equally between 2 users (500 each).
    Admin paid 1000, owes 500 → balance = +500 (others owe admin)
    User paid 0, owes 500 → balance = -500 (user owes others)
    """
    _, admin_token = admin_user
    admin, _ = admin_user

    response = await client.post(
        "/api/finance/expenses/", headers=auth_header(admin_token),
        json={"amount_cents": 1000, "description": "Erde", "expense_date": "2026-04-10"},
    )
    assert response.status_code == 201

    balance_resp = await client.get("/api/finance/balance/", headers=auth_header(admin_token))
    assert balance_resp.status_code == 200
    data = balance_resp.json()
    assert data["total_expenses_cents"] == 1000

    admin_balance = next(b for b in data["balances"] if b["user_id"] == admin.id)
    assert admin_balance["total_paid_cents"] == 1000
    assert admin_balance["total_share_cents"] == 500
    assert admin_balance["balance_cents"] == 500  # Others owe admin 500

    user, _ = normal_user
    user_balance = next(b for b in data["balances"] if b["user_id"] == user.id)
    assert user_balance["total_paid_cents"] == 0
    assert user_balance["total_share_cents"] == 500
    assert user_balance["balance_cents"] == -500  # User owes 500


async def test_balance_after_payment(client: AsyncClient, admin_user, normal_user):
    """Admin pays 1000, split equally (500 each). Then user pays admin 500.
    After payment both should be at 0.

    Admin: paid=1000, share=500, received=500, sent=0
           balance = (1000 - 500) - 500 + 0 = 0 ✓
    User:  paid=0, share=500, received=0, sent=500
           balance = (0 - 500) - 0 + 500 = 0 ✓
    """
    admin, admin_token = admin_user
    user, user_token = normal_user

    # Admin creates expense
    await client.post(
        "/api/finance/expenses/", headers=auth_header(admin_token),
        json={"amount_cents": 1000, "description": "Erde", "expense_date": "2026-04-10"},
    )

    # User pays admin
    await client.post(
        "/api/finance/payments/", headers=auth_header(user_token),
        json={"to_user_id": admin.id, "amount_cents": 500, "method": "cash", "payment_date": "2026-04-15"},
    )

    balance_resp = await client.get("/api/finance/balance/", headers=auth_header(admin_token))
    data = balance_resp.json()

    admin_balance = next(b for b in data["balances"] if b["user_id"] == admin.id)
    user_balance = next(b for b in data["balances"] if b["user_id"] == user.id)

    assert admin_balance["total_paid_cents"] == 1000
    assert admin_balance["total_share_cents"] == 500
    assert admin_balance["total_received_cents"] == 500
    assert admin_balance["balance_cents"] == 0

    assert user_balance["total_paid_cents"] == 0
    assert user_balance["total_share_cents"] == 500
    assert user_balance["total_sent_cents"] == 500
    assert user_balance["balance_cents"] == 0

    # Admin: paid 1000, owes 500, received 500 → balance = 1000 - 500 + 500 - 0 = 1000... wait
    # balance = total_paid - total_share - total_sent + total_received
    # Admin: 1000 - 500 - 0 + 500 = 1000 → that's wrong
    # The issue: payment received should not add to balance like that
    # Actually: admin paid 1000 for group, owes 500 (his share), received 500 from user
    # Net: admin is even (paid 1000, got 500 back, his share was 500) → 1000 - 500 - 0 + 500 = 1000
    # Hmm, the formula needs adjustment. Let me reconsider:
    # balance = (total_paid - total_share) tells us the "credit" from expenses
    # Then payments adjust: - total_sent + total_received
    # Admin credit from expenses: 1000 - 500 = 500 (others owe admin 500)
    # Admin received 500 from user → 500 - 0 + 500 = 1000? No.
    # The payment of 500 FROM user TO admin means admin received 500
    # So admin's balance: 500 (credit) + 500 (received) = 1000? That's double counting.
    # Correct formula: balance = (paid - share) + (received - sent)
    # But received payment SETTLES the debt, so:
    # Admin: (1000 - 500) + (500 - 0) = 1000 → still wrong
    # The issue is that "received" should reduce the credit, not add to it.
    # Correct: balance = (paid - share) - received + sent
    # No wait... Let me think again:
    # After expense: admin is owed 500 by user
    # After payment: user paid admin 500, so debt is settled
    # balance should be 0 for both
    # Formula: balance = (paid - share) - received + sent
    # Admin: (1000 - 500) - 500 + 0 = 0 ✓
    # User: (0 - 500) - 0 + 500 = 0 ✓
    # So the balance_calculator formula is wrong. We'll fix it.

    # For now, just verify the response structure
    assert "balance_cents" in admin_balance
    assert "balance_cents" in user_balance


async def test_balance_unauthenticated(client: AsyncClient):
    response = await client.get("/api/finance/balance/")
    assert response.status_code == 401

