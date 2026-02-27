from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import AdminUser, CurrentUser, DBSession
from app.finance import service
from app.finance.balance_calculator import calculate_balance
from app.finance.schemas import (
    BalanceOverview,
    ExpenseCategoryCreate,
    ExpenseCategoryRead,
    ExpenseCategoryUpdate,
    ExpenseCreate,
    ExpenseRead,
    ExpenseSplitRead,
    ExpenseUpdate,
    PaymentCreate,
    PaymentRead,
    PaymentUpdate,
)

category_router = APIRouter(prefix="/api/finance/categories", tags=["finance"])
expense_router = APIRouter(prefix="/api/finance/expenses", tags=["finance"])
payment_router = APIRouter(prefix="/api/finance/payments", tags=["finance"])
balance_router = APIRouter(prefix="/api/finance/balance", tags=["finance"])


# ─── Categories ────────────────────────────────────────────────────

@category_router.get("/", response_model=list[ExpenseCategoryRead])
async def list_categories(
    user: CurrentUser,
    db: DBSession,
    active_only: bool = Query(default=False),
):
    return await service.get_all_categories(db, active_only=active_only)


@category_router.post("/", response_model=ExpenseCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(data: ExpenseCategoryCreate, user: CurrentUser, db: DBSession):
    from sqlalchemy.exc import IntegrityError
    try:
        return await service.create_category(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{data.name}' already exists",
        )


@category_router.patch("/{category_id}", response_model=ExpenseCategoryRead)
async def update_category(
    category_id: int, data: ExpenseCategoryUpdate, user: CurrentUser, db: DBSession
):
    category = await service.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return await service.update_category(db, category, data)


# ─── Expenses ──────────────────────────────────────────────────────

@expense_router.get("/", response_model=list[ExpenseRead])
async def list_expenses(
    user: CurrentUser,
    db: DBSession,
    category_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return await service.get_all_expenses(
        db,
        category_id=category_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@expense_router.post("/", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
async def create_expense(data: ExpenseCreate, user: CurrentUser, db: DBSession):
    if data.category_id is not None:
        category = await service.get_category_by_id(db, data.category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    # Validate manual splits sum
    if data.splits:
        splits_sum = sum(s.share_amount_cents for s in data.splits)
        if splits_sum != data.amount_cents:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Splits sum ({splits_sum}) must equal amount ({data.amount_cents})",
            )
    expense = await service.create_expense(db, user.id, data)
    await db.refresh(expense)
    return expense


@expense_router.get("/{expense_id}", response_model=ExpenseRead)
async def get_expense(expense_id: int, user: CurrentUser, db: DBSession):
    expense = await service.get_expense_by_id(db, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@expense_router.patch("/{expense_id}", response_model=ExpenseRead)
async def update_expense(
    expense_id: int, data: ExpenseUpdate, user: CurrentUser, db: DBSession
):
    expense = await service.get_expense_by_id(db, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    updated = await service.update_expense(db, expense, data)
    await db.refresh(updated)
    return updated


@expense_router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(expense_id: int, user: CurrentUser, db: DBSession):
    expense = await service.get_expense_by_id(db, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    await service.delete_expense(db, expense)


# ─── Splits ────────────────────────────────────────────────────────

@expense_router.patch(
    "/{expense_id}/splits/{split_id}/settle", response_model=ExpenseSplitRead
)
async def settle_split(expense_id: int, split_id: int, user: CurrentUser, db: DBSession):
    split = await service.settle_split(db, split_id)
    if split is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Split not found")
    return split


@expense_router.patch(
    "/{expense_id}/splits/{split_id}/unsettle", response_model=ExpenseSplitRead
)
async def unsettle_split(expense_id: int, split_id: int, user: CurrentUser, db: DBSession):
    split = await service.unsettle_split(db, split_id)
    if split is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Split not found")
    return split


# ─── Payments ──────────────────────────────────────────────────────

@payment_router.get("/", response_model=list[PaymentRead])
async def list_payments(
    user: CurrentUser,
    db: DBSession,
    user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return await service.get_all_payments(
        db,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@payment_router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(data: PaymentCreate, user: CurrentUser, db: DBSession):
    if data.to_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot pay yourself",
        )
    payment = await service.create_payment(db, user.id, data)
    await db.refresh(payment)
    return payment


@payment_router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: int, user: CurrentUser, db: DBSession):
    payment = await service.get_payment_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@payment_router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: int, data: PaymentUpdate, user: CurrentUser, db: DBSession
):
    payment = await service.get_payment_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    # Only admin can confirm payments
    if data.confirmed_by_admin is not None and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can confirm payments",
        )
    updated = await service.update_payment(db, payment, data)
    await db.refresh(updated)
    return updated


@payment_router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(payment_id: int, user: CurrentUser, db: DBSession):
    payment = await service.get_payment_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    await service.delete_payment(db, payment)


# ─── Balance ───────────────────────────────────────────────────────

@balance_router.get("/", response_model=BalanceOverview)
async def get_balance(user: CurrentUser, db: DBSession):
    return await calculate_balance(db)

