from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.finance.models import (
    GardenExpense,
    MemberPayment,
    RecurringCost,
    StandingOrder,
    StandingOrderSkip,
)
from app.finance.schemas import GardenFundOverview, MemberBalance


def _months_active_in_year(
    valid_from: date, valid_to: date | None, year: int
) -> int:
    """Total months this cost/order is active in the given year (full year projection)."""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    start = max(valid_from, year_start)
    end = min(valid_to, year_end) if valid_to else year_end
    if start > end:
        return 0
    return (end.month - start.month + 1) + (end.year - start.year) * 12


def _active_months_list(
    valid_from: date, valid_to: date | None, year: int
) -> list[int]:
    """All months (1-12) this cost/order is active in the given year (full year)."""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    start = max(valid_from, year_start)
    end = min(valid_to, year_end) if valid_to else year_end
    if start > end:
        return []
    return list(range(start.month, end.month + 1))


def _completed_months_list(
    valid_from: date, valid_to: date | None, year: int, today: date
) -> list[int]:
    """Only months that are COMPLETED (in the past) for this year.

    A month counts as completed when the month is fully over.
    E.g. on 2026-02-28, only January (month 1) is completed.
    On 2026-03-01, January and February are completed.
    """
    all_months = _active_months_list(valid_from, valid_to, year)
    if not all_months:
        return []

    if today.year > year:
        # Entire year is in the past → all active months are completed
        return all_months

    if today.year < year:
        # Entire year is in the future → nothing completed
        return []

    # Same year: only months strictly before current month are completed
    current_month = today.month
    return [m for m in all_months if m < current_month]


def _projected_months_list(
    valid_from: date, valid_to: date | None, year: int, today: date
) -> list[int]:
    """Months that are NOT YET completed (current month + future).

    These are 'planned' but not yet countable as paid.
    """
    all_months = _active_months_list(valid_from, valid_to, year)
    completed = _completed_months_list(valid_from, valid_to, year, today)
    return [m for m in all_months if m not in completed]


def _completed_months_count_in_year(
    valid_from: date, valid_to: date | None, year: int, today: date
) -> int:
    """How many months of recurring cost have actually elapsed this year."""
    return len(_completed_months_list(valid_from, valid_to, year, today))


async def calculate_fund_overview(
    db: AsyncSession,
    year: int | None = None,
) -> GardenFundOverview:
    today = date.today()
    if year is None:
        year = today.year

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # ─── Recurring costs active in this year ───────────────────
    recurring_result = await db.execute(
        select(RecurringCost)
        .where(RecurringCost.is_active.is_(True))
        .where(RecurringCost.valid_from <= year_end)
        .where(
            (RecurringCost.valid_to.is_(None)) | (RecurringCost.valid_to >= year_start)
        )
    )
    recurring_costs = list(recurring_result.scalars().all())

    # Full-year projection (what the year WILL cost in total)
    total_monthly_base = 0
    total_from_monthly_projected = 0
    total_from_yearly = 0

    # Actual costs so far (only completed months)
    total_from_monthly_actual = 0

    for cost in recurring_costs:
        months_total = _months_active_in_year(cost.valid_from, cost.valid_to, year)
        months_completed = _completed_months_count_in_year(
            cost.valid_from, cost.valid_to, year, today
        )

        if cost.interval == "monthly":
            total_monthly_base += cost.amount_cents
            total_from_monthly_projected += cost.amount_cents * months_total
            total_from_monthly_actual += cost.amount_cents * months_completed
        elif cost.interval == "yearly":
            total_from_yearly += cost.amount_cents

    # Projected = full year; Actual = only completed months + yearly
    total_recurring_annual_projected = total_from_monthly_projected + total_from_yearly
    total_recurring_annual_actual = total_from_monthly_actual + total_from_yearly

    # ─── One-time expenses (shared only) ───────────────────────
    all_expenses_result = await db.execute(
        select(GardenExpense)
        .where(GardenExpense.expense_date >= year_start)
        .where(GardenExpense.expense_date <= year_end)
        .where(GardenExpense.is_shared.is_(True))
    )
    all_shared_expenses = list(all_expenses_result.scalars().all())

    admin_ids_result = await db.execute(
        select(User.id).where(User.role == "admin")
    )
    admin_ids = set(admin_ids_result.scalars().all())

    total_onetime = sum(
        e.amount_cents
        for e in all_shared_expenses
        if e.user_id in admin_ids or e.confirmed_by_admin
    )

    # Projected total (full year) vs actual total (so far)
    total_costs_annual_projected = total_recurring_annual_projected + total_onetime
    total_costs_annual_actual = total_recurring_annual_actual + total_onetime

    # ─── Active members ────────────────────────────────────────
    members_result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.display_name)
    )
    members = list(members_result.scalars().all())
    member_count = len(members) or 1

    # Per-member shares (projected = full year target)
    share_recurring_annual = total_recurring_annual_projected // member_count
    share_recurring_monthly = (
        share_recurring_annual // 12 if total_recurring_annual_projected > 0 else 0
    )
    share_onetime = total_onetime // member_count
    share_total_annual = total_costs_annual_projected // member_count
    share_total_monthly = (
        share_total_annual // 12 if total_costs_annual_projected > 0 else 0
    )

    # ─── Manual payments this year ─────────────────────────────
    payments_result = await db.execute(
        select(
            MemberPayment.for_user_id,
            func.coalesce(func.sum(MemberPayment.amount_cents), 0),
        )
        .where(MemberPayment.payment_date >= year_start)
        .where(MemberPayment.payment_date <= year_end)
        .where(MemberPayment.for_user_id.is_not(None))
        .group_by(MemberPayment.for_user_id)
    )
    payments_map = dict(payments_result.all())
    total_payments = sum(payments_map.values())

    # ─── Standing orders this year (ONLY COMPLETED MONTHS) ─────
    standing_result = await db.execute(
        select(StandingOrder)
        .where(StandingOrder.is_active.is_(True))
        .where(StandingOrder.valid_from <= year_end)
        .where(
            (StandingOrder.valid_to.is_(None))
            | (StandingOrder.valid_to >= year_start)
        )
    )
    standing_orders = list(standing_result.scalars().all())

    standing_map_actual: dict[int, int] = {}  # Only completed months
    standing_map_projected: dict[int, int] = {}  # Full year projection

    for order in standing_orders:
        skipped_months = {s.month for s in order.skips if s.year == year}

        # Completed months (past, actually paid)
        completed_months = _completed_months_list(
            order.valid_from, order.valid_to, year, today
        )
        paid_completed = [m for m in completed_months if m not in skipped_months]
        actual_total = order.amount_cents * len(paid_completed)
        standing_map_actual[order.user_id] = (
            standing_map_actual.get(order.user_id, 0) + actual_total
        )

        # Projected (full year, assuming future months will be paid)
        all_months = _active_months_list(order.valid_from, order.valid_to, year)
        paid_all = [m for m in all_months if m not in skipped_months]
        projected_total = order.amount_cents * len(paid_all)
        standing_map_projected[order.user_id] = (
            standing_map_projected.get(order.user_id, 0) + projected_total
        )

    total_standing_actual = sum(standing_map_actual.values())
    total_standing_projected = sum(standing_map_projected.values())

    total_income_actual = total_payments + total_standing_actual
    total_income_projected = total_payments + total_standing_projected

    # ─── Per-member balance ────────────────────────────────────
    member_balances = []
    for member in members:
        paid = payments_map.get(member.id, 0)
        standing_actual = standing_map_actual.get(member.id, 0)
        standing_projected = standing_map_projected.get(member.id, 0)

        income_actual = paid + standing_actual
        income_projected = paid + standing_projected

        remaining = share_total_annual - income_actual
        remaining_projected = share_total_annual - income_projected

        member_balances.append(
            MemberBalance(
                user_id=member.id,
                display_name=member.display_name,
                total_paid_cents=paid,
                total_standing_order_cents=standing_actual,
                total_standing_order_projected_cents=standing_projected,
                total_income_cents=income_actual,
                total_income_projected_cents=income_projected,
                share_recurring_cents=share_recurring_annual,
                share_onetime_cents=share_onetime,
                share_total_cents=share_total_annual,
                remaining_cents=remaining,
                remaining_projected_cents=remaining_projected,
            )
        )

    fund_balance = total_income_actual - total_onetime

    return GardenFundOverview(
        total_recurring_monthly_cents=total_monthly_base,
        total_recurring_yearly_cents=total_from_yearly,
        total_recurring_annual_cents=total_recurring_annual_projected,
        total_onetime_expenses_cents=total_onetime,
        total_costs_annual_cents=total_costs_annual_projected,
        total_payments_cents=total_payments,
        total_standing_order_cents=total_standing_actual,
        total_income_cents=total_income_actual,
        fund_balance_cents=fund_balance,
        share_recurring_per_member_annual_cents=share_recurring_annual,
        share_recurring_per_member_monthly_cents=share_recurring_monthly,
        share_onetime_per_member_cents=share_onetime,
        share_total_per_member_annual_cents=share_total_annual,
        share_total_per_member_monthly_cents=share_total_monthly,
        member_count=member_count,
        member_balances=member_balances,
    )

