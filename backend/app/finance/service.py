from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.finance.models import Expense, ExpenseCategory, ExpenseSplit, Payment
from app.finance.schemas import (
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCreate,
    ExpenseSplitInfo,
    ExpenseUpdate,
    PaymentCreate,
    PaymentUpdate,
)


# ─── Expense Categories ───────────────────────────────────────────

async def get_all_categories(db: AsyncSession, active_only: bool = False) -> list[ExpenseCategory]:
    stmt = select(ExpenseCategory).order_by(ExpenseCategory.name)
    if active_only:
        stmt = stmt.where(ExpenseCategory.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_id(db: AsyncSession, category_id: int) -> ExpenseCategory | None:
    result = await db.execute(
        select(ExpenseCategory).where(ExpenseCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, data: ExpenseCategoryCreate) -> ExpenseCategory:
    category = ExpenseCategory(**data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession, category: ExpenseCategory, data: ExpenseCategoryUpdate
) -> ExpenseCategory:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.flush()
    await db.refresh(category)
    return category


# ─── Expenses ──────────────────────────────────────────────────────

async def get_all_expenses(
    db: AsyncSession,
    *,
    category_id: int | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Expense]:
    stmt = select(Expense).order_by(Expense.expense_date.desc(), Expense.created_at.desc())

    if category_id is not None:
        stmt = stmt.where(Expense.category_id == category_id)
    if user_id is not None:
        stmt = stmt.where(Expense.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(Expense.expense_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Expense.expense_date <= date_to)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_expense_by_id(db: AsyncSession, expense_id: int) -> Expense | None:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    return result.scalar_one_or_none()


async def _get_active_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).where(User.is_active.is_(True)))
    return list(result.scalars().all())


async def create_expense(
    db: AsyncSession, user_id: int, data: ExpenseCreate
) -> Expense:
    expense_data = data.model_dump(exclude={"splits"})
    expense = Expense(user_id=user_id, **expense_data)
    db.add(expense)
    await db.flush()

    # Create splits
    if data.splits:
        # Manual splits provided
        for split_info in data.splits:
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=split_info.user_id,
                share_amount_cents=split_info.share_amount_cents,
            )
            db.add(split)
    else:
        # Auto-split equally among all active users
        active_users = await _get_active_users(db)
        if active_users:
            per_person = data.amount_cents // len(active_users)
            remainder = data.amount_cents % len(active_users)
            for i, user in enumerate(active_users):
                # First user gets the remainder cents
                share = per_person + (1 if i < remainder else 0)
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=user.id,
                    share_amount_cents=share,
                )
                db.add(split)

    await db.flush()
    await db.refresh(expense)
    return expense


async def update_expense(db: AsyncSession, expense: Expense, data: ExpenseUpdate) -> Expense:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    await db.flush()
    await db.refresh(expense)
    return expense


async def delete_expense(db: AsyncSession, expense: Expense) -> None:
    await db.delete(expense)
    await db.flush()


# ─── Expense Splits ───────────────────────────────────────────────

async def settle_split(db: AsyncSession, split_id: int) -> ExpenseSplit | None:
    result = await db.execute(select(ExpenseSplit).where(ExpenseSplit.id == split_id))
    split = result.scalar_one_or_none()
    if split:
        split.is_settled = True
        await db.flush()
        await db.refresh(split)
    return split


async def unsettle_split(db: AsyncSession, split_id: int) -> ExpenseSplit | None:
    result = await db.execute(select(ExpenseSplit).where(ExpenseSplit.id == split_id))
    split = result.scalar_one_or_none()
    if split:
        split.is_settled = False
        await db.flush()
        await db.refresh(split)
    return split


# ─── Payments ──────────────────────────────────────────────────────

async def get_all_payments(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.payment_date.desc(), Payment.created_at.desc())

    if user_id is not None:
        stmt = stmt.where(
            (Payment.from_user_id == user_id) | (Payment.to_user_id == user_id)
        )
    if date_from is not None:
        stmt = stmt.where(Payment.payment_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Payment.payment_date <= date_to)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_payment_by_id(db: AsyncSession, payment_id: int) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalar_one_or_none()


async def create_payment(db: AsyncSession, from_user_id: int, data: PaymentCreate) -> Payment:
    payment = Payment(from_user_id=from_user_id, **data.model_dump())
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment


async def update_payment(db: AsyncSession, payment: Payment, data: PaymentUpdate) -> Payment:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    await db.flush()
    await db.refresh(payment)
    return payment


async def delete_payment(db: AsyncSession, payment: Payment) -> None:
    await db.delete(payment)
    await db.flush()

