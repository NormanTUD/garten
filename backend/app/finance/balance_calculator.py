from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.finance.models import Expense, ExpenseSplit, Payment
from app.finance.schemas import BalanceOverview, UserBalance


async def calculate_balance(db: AsyncSession) -> BalanceOverview:
    """Calculate the financial balance for all active users.

    For each user:
    - total_paid = sum of expenses they created (they paid for the group)
    - total_share = sum of their splits (what they owe)
    - total_sent = sum of payments they sent
    - total_received = sum of payments they received
    - balance = total_paid - total_share - total_sent + total_received
      Positive = others owe you, Negative = you owe others
    """
    # Get all active users
    result = await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.display_name))
    users = list(result.scalars().all())

    # Total paid per user (expenses they created)
    paid_result = await db.execute(
        select(Expense.user_id, func.coalesce(func.sum(Expense.amount_cents), 0))
        .group_by(Expense.user_id)
    )
    paid_map = dict(paid_result.all())

    # Total share per user (their splits)
    share_result = await db.execute(
        select(ExpenseSplit.user_id, func.coalesce(func.sum(ExpenseSplit.share_amount_cents), 0))
        .group_by(ExpenseSplit.user_id)
    )
    share_map = dict(share_result.all())

    # Total sent per user
    sent_result = await db.execute(
        select(Payment.from_user_id, func.coalesce(func.sum(Payment.amount_cents), 0))
        .group_by(Payment.from_user_id)
    )
    sent_map = dict(sent_result.all())

    # Total received per user
    received_result = await db.execute(
        select(Payment.to_user_id, func.coalesce(func.sum(Payment.amount_cents), 0))
        .group_by(Payment.to_user_id)
    )
    received_map = dict(received_result.all())

    # Total expenses
    total_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount_cents), 0))
    )
    total_expenses = total_result.scalar() or 0

    balances = []
    for user in users:
        total_paid = paid_map.get(user.id, 0)
        total_share = share_map.get(user.id, 0)
        total_sent = sent_map.get(user.id, 0)
        total_received = received_map.get(user.id, 0)

        # balance = what you paid for others - what you owe - what you already sent + what you received
        balance = total_paid - total_share - total_sent + total_received

        balances.append(
            UserBalance(
                user_id=user.id,
                display_name=user.display_name,
                total_paid_cents=total_paid,
                total_share_cents=total_share,
                total_received_cents=total_received,
                total_sent_cents=total_sent,
                balance_cents=balance,
            )
        )

    return BalanceOverview(
        balances=balances,
        total_expenses_cents=total_expenses,
    )

