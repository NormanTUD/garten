from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.models import ExpenseCategory, GardenExpense, MemberPayment, RecurringCost
from app.finance.schemas import (
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    GardenExpenseCreate,
    GardenExpenseUpdate,
    MemberPaymentCreate,
    MemberPaymentUpdate,
    RecurringCostCreate,
    RecurringCostUpdate,
)

from app.finance.models import StandingOrder, StandingOrderSkip
from app.finance.schemas import StandingOrderCreate, StandingOrderUpdate, StandingOrderSkipCreate

# ─── Categories ────────────────────────────────────────────────────

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


async def get_category_by_name(db: AsyncSession, name: str) -> ExpenseCategory | None:
    result = await db.execute(
        select(ExpenseCategory).where(ExpenseCategory.name == name)
    )
    return result.scalar_one_or_none()


async def get_or_create_category(db: AsyncSession, name: str) -> ExpenseCategory:
    """Find category by name, or create it dynamically."""
    existing = await get_category_by_name(db, name)
    if existing:
        return existing
    category = ExpenseCategory(name=name)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


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


# ─── Recurring Costs ──────────────────────────────────────────────

async def get_all_recurring_costs(
    db: AsyncSession, active_only: bool = True, year: int | None = None
) -> list[RecurringCost]:
    stmt = select(RecurringCost).order_by(RecurringCost.description, RecurringCost.valid_from)
    if active_only:
        stmt = stmt.where(RecurringCost.is_active.is_(True))
    if year is not None:
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        # valid_from <= year_end AND (valid_to IS NULL OR valid_to >= year_start)
        stmt = stmt.where(RecurringCost.valid_from <= year_end)
        stmt = stmt.where(
            (RecurringCost.valid_to.is_(None)) | (RecurringCost.valid_to >= year_start)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_recurring_cost_by_id(db: AsyncSession, cost_id: int) -> RecurringCost | None:
    result = await db.execute(select(RecurringCost).where(RecurringCost.id == cost_id))
    return result.scalar_one_or_none()


async def create_recurring_cost(db: AsyncSession, data: RecurringCostCreate) -> RecurringCost:
    cost = RecurringCost(**data.model_dump())
    db.add(cost)
    await db.flush()
    await db.refresh(cost)
    return cost


async def update_recurring_cost(
    db: AsyncSession, cost: RecurringCost, data: RecurringCostUpdate
) -> RecurringCost:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cost, field, value)
    await db.flush()
    await db.refresh(cost)
    return cost


async def delete_recurring_cost(db: AsyncSession, cost: RecurringCost) -> None:
    await db.delete(cost)
    await db.flush()


# ─── Garden Expenses ──────────────────────────────────────────────

async def get_all_expenses(
    db: AsyncSession,
    *,
    category_id: int | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[GardenExpense]:
    stmt = select(GardenExpense).order_by(
        GardenExpense.expense_date.desc(), GardenExpense.created_at.desc()
    )
    if category_id is not None:
        stmt = stmt.where(GardenExpense.category_id == category_id)
    if user_id is not None:
        stmt = stmt.where(GardenExpense.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(GardenExpense.expense_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(GardenExpense.expense_date <= date_to)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_expense_by_id(db: AsyncSession, expense_id: int) -> GardenExpense | None:
    result = await db.execute(select(GardenExpense).where(GardenExpense.id == expense_id))
    return result.scalar_one_or_none()


async def create_expense(
    db: AsyncSession, user_id: int, data: GardenExpenseCreate
) -> GardenExpense:
    expense_data = data.model_dump(exclude={"category_name"})

    # Dynamic category: if category_name is set, find or create
    if data.category_name and not data.category_id:
        category = await get_or_create_category(db, data.category_name)
        expense_data["category_id"] = category.id

    expense = GardenExpense(user_id=user_id, **expense_data)
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return expense


async def update_expense(
    db: AsyncSession, expense: GardenExpense, data: GardenExpenseUpdate
) -> GardenExpense:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    await db.flush()
    await db.refresh(expense)
    return expense


async def delete_expense(db: AsyncSession, expense: GardenExpense) -> None:
    await db.delete(expense)
    await db.flush()


# ─── Member Payments ──────────────────────────────────────────────

async def get_all_payments(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[MemberPayment]:
    stmt = select(MemberPayment).order_by(
        MemberPayment.payment_date.desc(), MemberPayment.created_at.desc()
    )
    if user_id is not None:
        stmt = stmt.where(MemberPayment.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(MemberPayment.payment_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(MemberPayment.payment_date <= date_to)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_payment_by_id(db: AsyncSession, payment_id: int) -> MemberPayment | None:
    result = await db.execute(select(MemberPayment).where(MemberPayment.id == payment_id))
    return result.scalar_one_or_none()


async def create_payment(
    db: AsyncSession, user_id: int, data: MemberPaymentCreate
) -> MemberPayment:
    payment_data = data.model_dump()
    payment = MemberPayment(user_id=user_id, **payment_data)
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment

async def update_payment(
    db: AsyncSession, payment: MemberPayment, data: MemberPaymentUpdate
) -> MemberPayment:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    await db.flush()
    await db.refresh(payment)
    return payment


async def delete_payment(db: AsyncSession, payment: MemberPayment) -> None:
    await db.delete(payment)
    await db.flush()

# ─── Standing Orders ──────────────────────────────────────────────

async def get_all_standing_orders(
    db: AsyncSession, user_id: int | None = None, active_only: bool = True
) -> list[StandingOrder]:
    stmt = select(StandingOrder).order_by(StandingOrder.user_id, StandingOrder.valid_from)
    if user_id is not None:
        stmt = stmt.where(StandingOrder.user_id == user_id)
    if active_only:
        stmt = stmt.where(StandingOrder.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_standing_order_by_id(db: AsyncSession, order_id: int) -> StandingOrder | None:
    result = await db.execute(select(StandingOrder).where(StandingOrder.id == order_id))
    return result.scalar_one_or_none()


async def create_standing_order(db: AsyncSession, user_id: int, data: StandingOrderCreate) -> StandingOrder:
    order_data = data.model_dump(exclude={"user_id"})
    order = StandingOrder(user_id=user_id, **order_data)
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order


async def update_standing_order(
    db: AsyncSession, order: StandingOrder, data: StandingOrderUpdate
) -> StandingOrder:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.flush()
    await db.refresh(order)
    return order


async def delete_standing_order(db: AsyncSession, order: StandingOrder) -> None:
    await db.delete(order)
    await db.flush()


async def add_skip(db: AsyncSession, order_id: int, data: StandingOrderSkipCreate) -> StandingOrderSkip:
    skip = StandingOrderSkip(standing_order_id=order_id, **data.model_dump())
    db.add(skip)
    await db.flush()
    await db.refresh(skip)
    return skip


async def remove_skip(db: AsyncSession, skip_id: int) -> None:
    result = await db.execute(select(StandingOrderSkip).where(StandingOrderSkip.id == skip_id))
    skip = result.scalar_one_or_none()
    if skip:
        await db.delete(skip)
        await db.flush()

