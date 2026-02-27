from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.finance.models import GardenExpense, MemberPayment, RecurringCost
from app.finance.schemas import GardenFundOverview, MemberBalance


async def calculate_fund_overview(
    db: AsyncSession,
    year: int | None = None,
) -> GardenFundOverview:
    if year is None:
        year = date.today().year

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # ─── Recurring costs ───────────────────────────────────────
    recurring_result = await db.execute(
        select(RecurringCost).where(RecurringCost.is_active.is_(True))
    )
    recurring_costs = list(recurring_result.scalars().all())

    total_monthly = sum(c.amount_cents for c in recurring_costs if c.interval == "monthly")
    total_yearly = sum(c.amount_cents for c in recurring_costs if c.interval == "yearly")
    total_recurring_annual = (total_monthly * 12) + total_yearly

    # ─── One-time expenses this year ───────────────────────────
    onetime_result = await db.execute(
        select(func.coalesce(func.sum(GardenExpense.amount_cents), 0))
        .where(GardenExpense.expense_date >= year_start)
        .where(GardenExpense.expense_date <= year_end)
    )
    total_onetime = onetime_result.scalar() or 0

    total_costs_annual = total_recurring_annual + total_onetime

    # ─── Active members ────────────────────────────────────────
    members_result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.display_name)
    )
    members = list(members_result.scalars().all())
    member_count = len(members) or 1

    # Getrennte Anteile
    share_recurring_annual = total_recurring_annual // member_count
    share_recurring_monthly = share_recurring_annual // 12
    share_onetime = total_onetime // member_count
    share_total_annual = total_costs_annual // member_count
    share_total_monthly = share_total_annual // 12

    # ─── Payments this year per member ─────────────────────────
    payments_result = await db.execute(
        select(MemberPayment.user_id, func.coalesce(func.sum(MemberPayment.amount_cents), 0))
        .where(MemberPayment.payment_date >= year_start)
        .where(MemberPayment.payment_date <= year_end)
        .group_by(MemberPayment.user_id)
    )
    payments_map = dict(payments_result.all())

    total_payments = sum(payments_map.values())

    # ─── Per-member balance ────────────────────────────────────
    member_balances = []
    for member in members:
        paid = payments_map.get(member.id, 0)
        remaining = share_total_annual - paid

        member_balances.append(
            MemberBalance(
                user_id=member.id,
                display_name=member.display_name,
                total_paid_cents=paid,
                share_recurring_cents=share_recurring_annual,
                share_onetime_cents=share_onetime,
                share_total_cents=share_total_annual,
                remaining_cents=remaining,
            )
        )

    fund_balance = total_payments - total_onetime

    return GardenFundOverview(
        total_recurring_monthly_cents=total_monthly,
        total_recurring_yearly_cents=total_yearly,
        total_recurring_annual_cents=total_recurring_annual,
        total_onetime_expenses_cents=total_onetime,
        total_costs_annual_cents=total_costs_annual,
        total_payments_cents=total_payments,
        fund_balance_cents=fund_balance,
        share_recurring_per_member_annual_cents=share_recurring_annual,
        share_recurring_per_member_monthly_cents=share_recurring_monthly,
        share_onetime_per_member_cents=share_onetime,
        share_total_per_member_annual_cents=share_total_annual,
        share_total_per_member_monthly_cents=share_total_monthly,
        member_count=member_count,
        member_balances=member_balances,
    )

