from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.finance.models import GardenExpense, MemberPayment, RecurringCost, StandingOrder, StandingOrderSkip
from app.finance.schemas import GardenFundOverview, MemberBalance


def _months_active_in_year(valid_from: date, valid_to: date | None, year: int) -> int:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    start = max(valid_from, year_start)
    end = min(valid_to, year_end) if valid_to else year_end
    if start > end:
        return 0
    return (end.month - start.month + 1) + (end.year - start.year) * 12


def _active_months_list(valid_from: date, valid_to: date | None, year: int) -> list[int]:
    """Return list of month numbers (1-12) where a standing order is active."""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    start = max(valid_from, year_start)
    end = min(valid_to, year_end) if valid_to else year_end
    if start > end:
        return []
    return list(range(start.month, end.month + 1))


async def calculate_fund_overview(
    db: AsyncSession,
    year: int | None = None,
) -> GardenFundOverview:
    if year is None:
        year = date.today().year

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

    total_monthly_base = 0
    total_from_monthly = 0
    total_from_yearly = 0

    for cost in recurring_costs:
        months = _months_active_in_year(cost.valid_from, cost.valid_to, year)
        if cost.interval == "monthly":
            total_monthly_base += cost.amount_cents
            total_from_monthly += cost.amount_cents * months
        elif cost.interval == "yearly":
            total_from_yearly += cost.amount_cents

    total_recurring_annual = total_from_monthly + total_from_yearly

    # ─── One-time expenses (shared only) ───────────────────────
    onetime_result = await db.execute(
        select(func.coalesce(func.sum(GardenExpense.amount_cents), 0))
        .where(GardenExpense.expense_date >= year_start)
        .where(GardenExpense.expense_date <= year_end)
        .where(GardenExpense.is_shared.is_(True))
    )
    total_onetime = onetime_result.scalar() or 0

    total_costs_annual = total_recurring_annual + total_onetime

    # ─── Active members ────────────────────────────────────────
    members_result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.display_name)
    )
    members = list(members_result.scalars().all())
    member_count = len(members) or 1

    share_recurring_annual = total_recurring_annual // member_count
    share_recurring_monthly = share_recurring_annual // 12 if total_recurring_annual > 0 else 0
    share_onetime = total_onetime // member_count
    share_total_annual = total_costs_annual // member_count
    share_total_monthly = share_total_annual // 12 if total_costs_annual > 0 else 0

    # ─── Manual payments this year ─────────────────────────────
    payments_result = await db.execute(
        select(MemberPayment.for_user_id, func.coalesce(func.sum(MemberPayment.amount_cents), 0))
        .where(MemberPayment.payment_date >= year_start)
        .where(MemberPayment.payment_date <= year_end)
        .where(MemberPayment.for_user_id.is_not(None))
        .group_by(MemberPayment.for_user_id)
    )
    payments_map = dict(payments_result.all())
    total_payments = sum(payments_map.values())

    # ─── Standing orders this year ─────────────────────────────
    standing_result = await db.execute(
        select(StandingOrder)
        .where(StandingOrder.is_active.is_(True))
        .where(StandingOrder.valid_from <= year_end)
        .where(
            (StandingOrder.valid_to.is_(None)) | (StandingOrder.valid_to >= year_start)
        )
    )
    standing_orders = list(standing_result.scalars().all())

    # Calculate per-user standing order totals
    standing_map: dict[int, int] = {}  # user_id -> total cents paid via standing orders
    for order in standing_orders:
        active_months = _active_months_list(order.valid_from, order.valid_to, year)
        skipped_months = {s.month for s in order.skips if s.year == year}
        paid_months = [m for m in active_months if m not in skipped_months]
        total = order.amount_cents * len(paid_months)
        standing_map[order.user_id] = standing_map.get(order.user_id, 0) + total

    total_standing = sum(standing_map.values())
    total_income = total_payments + total_standing

    # ─── Per-member balance ────────────────────────────────────
    member_balances = []
    for member in members:
        paid = payments_map.get(member.id, 0)
        standing = standing_map.get(member.id, 0)
        income = paid + standing
        remaining = share_total_annual - income

        member_balances.append(
            MemberBalance(
                user_id=member.id,
                display_name=member.display_name,
                total_paid_cents=paid,
                total_standing_order_cents=standing,
                total_income_cents=income,
                share_recurring_cents=share_recurring_annual,
                share_onetime_cents=share_onetime,
                share_total_cents=share_total_annual,
                remaining_cents=remaining,
            )
        )

    fund_balance = total_income - total_onetime

    return GardenFundOverview(
        total_recurring_monthly_cents=total_monthly_base,
        total_recurring_yearly_cents=total_from_yearly,
        total_recurring_annual_cents=total_recurring_annual,
        total_onetime_expenses_cents=total_onetime,
        total_costs_annual_cents=total_costs_annual,
        total_payments_cents=total_payments,
        total_standing_order_cents=total_standing,
        total_income_cents=total_income,
        fund_balance_cents=fund_balance,
        share_recurring_per_member_annual_cents=share_recurring_annual,
        share_recurring_per_member_monthly_cents=share_recurring_monthly,
        share_onetime_per_member_cents=share_onetime,
        share_total_per_member_annual_cents=share_total_annual,
        share_total_per_member_monthly_cents=share_total_monthly,
        member_count=member_count,
        member_balances=member_balances,
    )
