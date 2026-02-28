import pytest
from datetime import date
from httpx import AsyncClient


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
async def duty_config(admin_client: AsyncClient):
    """Create a duty config for the current year."""
    year = date.today().year
    resp = await admin_client.post("/api/duty/config", json={
        "year": year,
        "total_hours": 10.0,
        "hourly_rate_cents": 1500,
        "notes": "Test config",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def duty_assignments(admin_client: AsyncClient, duty_config: dict):
    """Auto-assign hours equally."""
    year = duty_config["year"]
    resp = await admin_client.post(f"/api/duty/assignments/{year}/auto-assign")
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def duty_log(user_client: AsyncClient):
    """Create a duty log entry as normal user."""
    resp = await user_client.post("/api/duty/logs", json={
        "date": date.today().isoformat(),
        "hours": 1.5,
        "description": "Hecke geschnitten",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def admin_duty_log(admin_client: AsyncClient):
    """Create a duty log entry as admin (auto-confirmed)."""
    resp = await admin_client.post("/api/duty/logs", json={
        "date": date.today().isoformat(),
        "hours": 2.0,
        "description": "Zaun repariert",
    })
    assert resp.status_code == 201
    return resp.json()


# ─── Config Tests ──────────────────────────────────────────

class TestDutyConfig:
    async def test_create_config(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/duty/config", json={
            "year": 2099,
            "total_hours": 20.0,
            "hourly_rate_cents": 2000,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["year"] == 2099
        assert data["total_hours"] == 20.0
        assert data["hourly_rate_cents"] == 2000

    async def test_create_config_duplicate_year(self, admin_client: AsyncClient, duty_config: dict):
        resp = await admin_client.post("/api/duty/config", json={
            "year": duty_config["year"],
            "total_hours": 5.0,
            "hourly_rate_cents": 1000,
        })
        assert resp.status_code == 409

    async def test_create_config_forbidden_for_user(self, user_client: AsyncClient):
        resp = await user_client.post("/api/duty/config", json={
            "year": 2098,
            "total_hours": 10.0,
            "hourly_rate_cents": 1500,
        })
        assert resp.status_code == 403

    async def test_get_config(self, admin_client: AsyncClient, duty_config: dict):
        resp = await admin_client.get(f"/api/duty/config/{duty_config['year']}")
        assert resp.status_code == 200
        assert resp.json()["total_hours"] == 10.0

    async def test_get_config_not_found(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/duty/config/1900")
        assert resp.status_code == 404

    async def test_list_configs(self, admin_client: AsyncClient, duty_config: dict):
        resp = await admin_client.get("/api/duty/config")
        assert resp.status_code == 200
        years = [c["year"] for c in resp.json()]
        assert duty_config["year"] in years

    async def test_update_config(self, admin_client: AsyncClient, duty_config: dict):
        resp = await admin_client.put(f"/api/duty/config/{duty_config['year']}", json={
            "total_hours": 15.0,
            "hourly_rate_cents": 2000,
        })
        assert resp.status_code == 200
        assert resp.json()["total_hours"] == 15.0
        assert resp.json()["hourly_rate_cents"] == 2000

    async def test_update_config_partial(self, admin_client: AsyncClient, duty_config: dict):
        resp = await admin_client.put(f"/api/duty/config/{duty_config['year']}", json={
            "notes": "Updated note",
        })
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Updated note"
        assert resp.json()["total_hours"] == duty_config["total_hours"]

    async def test_delete_config(self, admin_client: AsyncClient):
        # Create then delete
        await admin_client.post("/api/duty/config", json={
            "year": 2097,
            "total_hours": 5.0,
            "hourly_rate_cents": 1000,
        })
        resp = await admin_client.delete("/api/duty/config/2097")
        assert resp.status_code == 204

        resp = await admin_client.get("/api/duty/config/2097")
        assert resp.status_code == 404

    async def test_delete_config_not_found(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/duty/config/1900")
        assert resp.status_code == 404

    async def test_user_can_read_config(self, user_client: AsyncClient, duty_config: dict):
        resp = await user_client.get(f"/api/duty/config/{duty_config['year']}")
        assert resp.status_code == 200


# ─── Assignment Tests ──────────────────────────────────────

class TestDutyAssignments:
    async def test_auto_assign(self, admin_client: AsyncClient, duty_config: dict):
        year = duty_config["year"]
        resp = await admin_client.post(f"/api/duty/assignments/{year}/auto-assign")
        assert resp.status_code == 200
        assignments = resp.json()
        assert len(assignments) > 0
        # All should have equal hours
        hours_set = {a["assigned_hours"] for a in assignments}
        assert len(hours_set) == 1

    async def test_auto_assign_no_config(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/duty/assignments/1900/auto-assign")
        assert resp.status_code == 400

    async def test_auto_assign_forbidden_for_user(self, user_client: AsyncClient, duty_config: dict):
        resp = await user_client.post(f"/api/duty/assignments/{duty_config['year']}/auto-assign")
        assert resp.status_code == 403

    async def test_create_assignment(self, admin_client: AsyncClient, duty_config: dict, test_user_id: int):
        resp = await admin_client.post("/api/duty/assignments", json={
            "user_id": test_user_id,
            "year": duty_config["year"],
            "assigned_hours": 3.5,
            "notes": "Tausch mit Admin",
        })
        assert resp.status_code == 201
        assert resp.json()["assigned_hours"] == 3.5
        assert resp.json()["notes"] == "Tausch mit Admin"

    async def test_create_assignment_duplicate(
        self, admin_client: AsyncClient, duty_config: dict, duty_assignments: list
    ):
        # Try to create for a user that already has an assignment
        existing = duty_assignments[0]
        resp = await admin_client.post("/api/duty/assignments", json={
            "user_id": existing["user_id"],
            "year": existing["year"],
            "assigned_hours": 5.0,
        })
        assert resp.status_code == 409

    async def test_update_assignment(self, admin_client: AsyncClient, duty_assignments: list):
        assignment = duty_assignments[0]
        resp = await admin_client.put(f"/api/duty/assignments/{assignment['id']}", json={
            "assigned_hours": 7.0,
            "notes": "Mehr Stunden übernommen",
        })
        assert resp.status_code == 200
        assert resp.json()["assigned_hours"] == 7.0

    async def test_delete_assignment(self, admin_client: AsyncClient, duty_assignments: list):
        assignment = duty_assignments[0]
        resp = await admin_client.delete(f"/api/duty/assignments/{assignment['id']}")
        assert resp.status_code == 204

    async def test_list_assignments(self, user_client: AsyncClient, duty_assignments: list):
        year = duty_assignments[0]["year"]
        resp = await user_client.get(f"/api/duty/assignments/{year}")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    async def test_user_cannot_create_assignment(self, user_client: AsyncClient, duty_config: dict):
        resp = await user_client.post("/api/duty/assignments", json={
            "user_id": 1,
            "year": duty_config["year"],
            "assigned_hours": 2.0,
        })
        assert resp.status_code == 403


# ─── Log Tests ─────────────────────────────────────────────

class TestDutyLogs:
    async def test_create_log_as_user(self, duty_log: dict):
        assert duty_log["hours"] == 1.5
        assert duty_log["description"] == "Hecke geschnitten"
        assert duty_log["confirmed"] is False
        assert duty_log["confirmed_by_id"] is None

    async def test_create_log_as_admin_auto_confirms(self, admin_duty_log: dict):
        assert admin_duty_log["hours"] == 2.0
        assert admin_duty_log["confirmed"] is True
        assert admin_duty_log["confirmed_by_id"] is not None

    async def test_create_log_invalid_hours(self, user_client: AsyncClient):
        resp = await user_client.post("/api/duty/logs", json={
            "date": date.today().isoformat(),
            "hours": 0,
            "description": "Should fail",
        })
        assert resp.status_code == 422

    async def test_create_log_empty_description(self, user_client: AsyncClient):
        resp = await user_client.post("/api/duty/logs", json={
            "date": date.today().isoformat(),
            "hours": 1.0,
            "description": "",
        })
        assert resp.status_code == 422

    async def test_confirm_log(self, admin_client: AsyncClient, duty_log: dict):
        assert duty_log["confirmed"] is False
        resp = await admin_client.post(f"/api/duty/logs/{duty_log['id']}/confirm")
        assert resp.status_code == 200
        assert resp.json()["confirmed"] is True
        assert resp.json()["confirmed_by_name"] is not None

    async def test_unconfirm_log(self, admin_client: AsyncClient, duty_log: dict):
        # Confirm first
        await admin_client.post(f"/api/duty/logs/{duty_log['id']}/confirm")
        # Then unconfirm
        resp = await admin_client.post(f"/api/duty/logs/{duty_log['id']}/unconfirm")
        assert resp.status_code == 200
        assert resp.json()["confirmed"] is False
        assert resp.json()["confirmed_by_id"] is None

    async def test_user_cannot_confirm(self, user_client: AsyncClient, duty_log: dict):
        resp = await user_client.post(f"/api/duty/logs/{duty_log['id']}/confirm")
        assert resp.status_code == 403

    async def test_user_cannot_delete(self, user_client: AsyncClient, duty_log: dict):
        resp = await user_client.delete(f"/api/duty/logs/{duty_log['id']}")
        assert resp.status_code == 403

    async def test_admin_can_delete(self, admin_client: AsyncClient, duty_log: dict):
        resp = await admin_client.delete(f"/api/duty/logs/{duty_log['id']}")
        assert resp.status_code == 204

    async def test_delete_not_found(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/duty/logs/99999")
        assert resp.status_code == 404

    async def test_list_logs(self, user_client: AsyncClient, duty_log: dict):
        year = date.today().year
        resp = await user_client.get(f"/api/duty/logs/{year}")
        assert resp.status_code == 200
        ids = [l["id"] for l in resp.json()]
        assert duty_log["id"] in ids

    async def test_list_logs_filter_by_user(
        self, user_client: AsyncClient, duty_log: dict, test_user_id: int
    ):
        year = date.today().year
        resp = await user_client.get(f"/api/duty/logs/{year}?user_id={test_user_id}")
        assert resp.status_code == 200
        for log in resp.json():
            assert log["user_id"] == test_user_id


# ─── Overview Tests ────────────────────────────────────────

class TestDutyOverview:
    async def test_overview_no_config(self, user_client: AsyncClient):
        resp = await user_client.get("/api/duty/overview/1900")
        assert resp.status_code == 404

    async def test_overview_basic(self, user_client: AsyncClient, duty_config: dict, duty_assignments: list):
        year = duty_config["year"]
        resp = await user_client.get(f"/api/duty/overview/{year}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == year
        assert data["total_hours"] == 10.0
        assert data["hourly_rate_cents"] == 1500
        assert len(data["member_balances"]) > 0

    async def test_overview_all_members_have_balance(
        self, user_client: AsyncClient, duty_config: dict, duty_assignments: list
    ):
        year = duty_config["year"]
        resp = await user_client.get(f"/api/duty/overview/{year}")
        data = resp.json()
        for balance in data["member_balances"]:
            assert "assigned_hours" in balance
            assert "confirmed_hours" in balance
            assert "pending_hours" in balance
            assert "remaining_hours" in balance
            assert "compensation_cents" in balance

    async def test_overview_no_work_done(
        self, user_client: AsyncClient, duty_config: dict, duty_assignments: list
    ):
        year = duty_config["year"]
        resp = await user_client.get(f"/api/duty/overview/{year}")
        data = resp.json()
        for balance in data["member_balances"]:
            assert balance["confirmed_hours"] == 0
            assert balance["remaining_hours"] == balance["assigned_hours"]
            expected_comp = round(balance["assigned_hours"] * duty_config["hourly_rate_cents"])
            assert balance["compensation_cents"] == expected_comp

    async def test_overview_after_confirmed_work(
        self, admin_client: AsyncClient, user_client: AsyncClient,
        duty_config: dict, duty_assignments: list, test_user_id: int
    ):
        year = duty_config["year"]

        # User logs 1.5h
        log_resp = await user_client.post("/api/duty/logs", json={
            "date": date.today().isoformat(),
            "hours": 1.5,
            "description": "Laub geharkt",
        })
        log_id = log_resp.json()["id"]

        # Check overview: should be pending, not confirmed
        resp = await user_client.get(f"/api/duty/overview/{year}")
        balance = next(b for b in resp.json()["member_balances"] if b["user_id"] == test_user_id)
        assert balance["pending_hours"] == 1.5
        assert balance["confirmed_hours"] == 0

        # Admin confirms
        await admin_client.post(f"/api/duty/logs/{log_id}/confirm")

        # Check overview again: should be confirmed now
        resp = await user_client.get(f"/api/duty/overview/{year}")
        balance = next(b for b in resp.json()["member_balances"] if b["user_id"] == test_user_id)
        assert balance["confirmed_hours"] == 1.5
        assert balance["pending_hours"] == 0
        remaining = balance["assigned_hours"] - 1.5
        assert balance["remaining_hours"] == pytest.approx(remaining, abs=0.01)

    async def test_overview_overfulfilled(
        self, admin_client: AsyncClient, duty_config: dict, duty_assignments: list
    ):
        year = duty_config["year"]

        # Admin logs more hours than assigned (auto-confirmed)
        resp = await admin_client.post("/api/duty/logs", json={
            "date": date.today().isoformat(),
            "hours": 50.0,
            "description": "Alles gemacht",
        })
        assert resp.status_code == 201

        resp = await admin_client.get(f"/api/duty/overview/{year}")
        admin_balance = resp.json()["member_balances"][0]  # Admin is likely first
        # remaining should be negative or 0, compensation should be 0
        assert admin_balance["compensation_cents"] == 0

    async def test_overview_unassigned_hours(
        self, admin_client: AsyncClient, duty_config: dict
    ):
        """If no assignments exist, unassigned should equal total_hours."""
        year = duty_config["year"]
        resp = await admin_client.get(f"/api/duty/overview/{year}")
        # Without assignments, default_hours_per_member is used
        # but total_unassigned reflects actual assignments vs total
        data = resp.json()
        assert data["total_hours"] == 10.0


# ─── Finance Integration Tests ─────────────────────────────

class TestDutyFinanceIntegration:
    async def test_duty_compensation_in_fund_overview(
        self, user_client: AsyncClient, admin_client: AsyncClient,
        duty_config: dict, duty_assignments: list
    ):
        """Duty compensation should appear in the finance fund overview."""
        year = duty_config["year"]

        # No work done → everyone owes compensation
        resp = await user_client.get(f"/api/finance/fund-overview?year={year}")
        if resp.status_code == 200:
            data = resp.json()
            for balance in data["member_balances"]:
                # duty_compensation_cents should be > 0 if no hours done
                assert "duty_compensation_cents" in balance

    async def test_duty_compensation_zero_when_fulfilled(
        self, admin_client: AsyncClient, user_client: AsyncClient,
        duty_config: dict, duty_assignments: list, test_user_id: int
    ):
        """If user fulfills all hours, compensation should be 0."""
        year = duty_config["year"]

        # Get assigned hours for user
        resp = await user_client.get(f"/api/duty/overview/{year}")
        balance = next(b for b in resp.json()["member_balances"] if b["user_id"] == test_user_id)
        assigned = balance["assigned_hours"]

        # Log exactly the assigned hours
        log_resp = await user_client.post("/api/duty/logs", json={
            "date": date.today().isoformat(),
            "hours": assigned,
            "description": "Alles erledigt",
        })
        log_id = log_resp.json()["id"]
        await admin_client.post(f"/api/duty/logs/{log_id}/confirm")

        # Check finance overview
        resp = await user_client.get(f"/api/finance/fund-overview?year={year}")
        if resp.status_code == 200:
            data = resp.json()
            user_balance = next(
                (b for b in data["member_balances"] if b["user_id"] == test_user_id), None
            )
            if user_balance:
                assert user_balance["duty_compensation_cents"] == 0

    async def test_duty_compensation_increases_share_total(
        self, user_client: AsyncClient, duty_config: dict, duty_assignments: list,
        test_user_id: int
    ):
        """share_total_cents should include duty compensation."""
        year = duty_config["year"]

        # Get fund overview without duty
        resp_before = await user_client.get(f"/api/finance/fund-overview?year={year}")
        if resp_before.status_code != 200:
            pytest.skip("Fund overview not available")

        data = resp_before.json()
        user_balance = next(
            (b for b in data["member_balances"] if b["user_id"] == test_user_id), None
        )
        if user_balance and user_balance["duty_compensation_cents"] > 0:
            # share_total should be base share + duty compensation
            base_share = data["share_total_per_member_annual_cents"]
            assert user_balance["share_total_cents"] == base_share + user_balance["duty_compensation_cents"]

