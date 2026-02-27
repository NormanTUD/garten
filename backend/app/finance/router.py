import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import AdminUser, CurrentUser, DBSession
from app.finance import service
from app.finance.balance_calculator import calculate_fund_overview
from app.finance.schemas import (
    ExpenseCategoryCreate,
    ExpenseCategoryRead,
    ExpenseCategoryUpdate,
    GardenExpenseCreate,
    GardenExpenseRead,
    GardenExpenseUpdate,
    GardenFundOverview,
    MemberPaymentCreate,
    MemberPaymentRead,
    MemberPaymentUpdate,
    RecurringCostCreate,
    RecurringCostRead,
    RecurringCostUpdate,
    StandingOrderCreate,
    StandingOrderRead,
    StandingOrderSkipCreate,
    StandingOrderSkipRead,
    StandingOrderUpdate,
)


category_router = APIRouter(prefix="/api/finance/categories", tags=["finance"])
recurring_router = APIRouter(prefix="/api/finance/recurring", tags=["finance"])
expense_router = APIRouter(prefix="/api/finance/expenses", tags=["finance"])
payment_router = APIRouter(prefix="/api/finance/payments", tags=["finance"])
fund_router = APIRouter(prefix="/api/finance/fund", tags=["finance"])
receipt_router = APIRouter(prefix="/api/finance/receipts", tags=["finance"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ─── Categories ────────────────────────────────────────────────────

@category_router.get("/", response_model=list[ExpenseCategoryRead])
async def list_categories(user: CurrentUser, db: DBSession, active_only: bool = Query(default=False)):
    return await service.get_all_categories(db, active_only=active_only)


@category_router.post("/", response_model=ExpenseCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(data: ExpenseCategoryCreate, user: CurrentUser, db: DBSession):
    try:
        return await service.create_category(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{data.name}' already exists",
        )


@category_router.patch("/{category_id}", response_model=ExpenseCategoryRead)
async def update_category(category_id: int, data: ExpenseCategoryUpdate, user: CurrentUser, db: DBSession):
    category = await service.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return await service.update_category(db, category, data)


# ─── Recurring Costs ──────────────────────────────────────────────

@recurring_router.get("/", response_model=list[RecurringCostRead])
async def list_recurring_costs(
    user: CurrentUser,
    db: DBSession,
    active_only: bool = Query(default=True),
    year: int | None = Query(default=None),
):
    return await service.get_all_recurring_costs(db, active_only=active_only, year=year)


@recurring_router.post("/", response_model=RecurringCostRead, status_code=status.HTTP_201_CREATED)
async def create_recurring_cost(data: RecurringCostCreate, user: AdminUser, db: DBSession):
    """Only admin can create recurring costs (rent, water, insurance, etc.)."""
    return await service.create_recurring_cost(db, data)


@recurring_router.patch("/{cost_id}", response_model=RecurringCostRead)
async def update_recurring_cost(cost_id: int, data: RecurringCostUpdate, user: AdminUser, db: DBSession):
    cost = await service.get_recurring_cost_by_id(db, cost_id)
    if cost is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring cost not found")
    return await service.update_recurring_cost(db, cost, data)


@recurring_router.delete("/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_cost(cost_id: int, user: AdminUser, db: DBSession):
    cost = await service.get_recurring_cost_by_id(db, cost_id)
    if cost is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring cost not found")
    await service.delete_recurring_cost(db, cost)


# ─── Garden Expenses ──────────────────────────────────────────────

@expense_router.get("/", response_model=list[GardenExpenseRead])
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
        db, category_id=category_id, user_id=user_id,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
    )


@expense_router.post("/", response_model=GardenExpenseRead, status_code=status.HTTP_201_CREATED)
async def create_expense(data: GardenExpenseCreate, user: CurrentUser, db: DBSession):
    expense = await service.create_expense(db, user.id, data)
    await db.refresh(expense)

    # If non-admin creates a shared expense → notify all admins
    if data.is_shared and user.role != "admin":
        from app.messaging import service as msg_service
        from app.auth.models import User
        from sqlalchemy import select

        result = await db.execute(
            select(User).where(User.role == "admin").where(User.is_active.is_(True))
        )
        admins = list(result.scalars().all())

        amount_str = f"{expense.amount_cents / 100:.2f} €"
        for admin in admins:
            await msg_service.send_system_message(
                db,
                recipient_id=admin.id,
                subject=f"Ausgabe zur Bestätigung: {expense.description}",
                body=(
                    f"{user.display_name} hat eine Ausgabe von {amount_str} eingetragen "
                    f"und möchte sie auf alle umlegen:\n\n"
                    f"Beschreibung: {expense.description}\n"
                    f"Betrag: {amount_str}\n"
                    f"Datum: {expense.expense_date}\n\n"
                    f"Bitte bestätige die Umlage in der Finanzübersicht."
                ),
                message_type="auto:expense_approval",
                related_entity="expense",
                related_entity_id=expense.id,
            )

    return expense


@expense_router.patch("/{expense_id}/confirm", response_model=GardenExpenseRead)
async def confirm_expense(expense_id: int, admin: AdminUser, db: DBSession):
    """Admin confirms a shared expense. Marks related messages as read."""
    from sqlalchemy import select, update
    from app.finance.models import GardenExpense
    from app.messaging.models import Message

    result = await db.execute(select(GardenExpense).where(GardenExpense.id == expense_id))
    expense = result.scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    if expense.confirmed_by_admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already confirmed")

    # Confirm
    expense.confirmed_by_admin = True
    expense.confirmed_by_id = admin.id
    await db.flush()

    # Mark all related approval messages as read for all admins
    await db.execute(
        update(Message)
        .where(Message.related_entity == "expense")
        .where(Message.related_entity_id == expense_id)
        .where(Message.message_type == "auto:expense_approval")
        .values(is_read=True)
    )
    await db.flush()

    # Notify the expense creator
    from app.messaging import service as msg_service
    amount_str = f"{expense.amount_cents / 100:.2f} €"
    await msg_service.send_system_message(
        db,
        recipient_id=expense.user_id,
        subject=f"Ausgabe bestätigt ✓: {expense.description}",
        body=(
            f"Deine Ausgabe von {amount_str} ({expense.description}) wurde von "
            f"{admin.display_name} bestätigt und wird auf alle umgelegt."
        ),
        message_type="auto:expense_confirmed",
        related_entity="expense",
        related_entity_id=expense.id,
    )

    await db.refresh(expense)
    return expense

@expense_router.get("/{expense_id}", response_model=GardenExpenseRead)
async def get_expense(expense_id: int, user: CurrentUser, db: DBSession):
    expense = await service.get_expense_by_id(db, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@expense_router.patch("/{expense_id}", response_model=GardenExpenseRead)
async def update_expense(expense_id: int, data: GardenExpenseUpdate, user: CurrentUser, db: DBSession):
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


# ─── Member Payments ──────────────────────────────────────────────

@payment_router.get("/", response_model=list[MemberPaymentRead])
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
        db, user_id=user_id, date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )


@payment_router.post("/", response_model=MemberPaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(data: MemberPaymentCreate, user: CurrentUser, db: DBSession):
    """Create a payment into the garden fund.

    - Normal user: payment is for themselves
    - Admin: can set for_user_id to credit another user
    """
    if data.for_user_id is not None and data.for_user_id != user.id:
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can create payments for other users",
            )
    # If no for_user_id set, it's for the current user
    if data.for_user_id is None:
        data.for_user_id = user.id
    payment = await service.create_payment(db, user.id, data)
    await db.refresh(payment)
    return payment

@payment_router.get("/{payment_id}", response_model=MemberPaymentRead)
async def get_payment(payment_id: int, user: CurrentUser, db: DBSession):
    payment = await service.get_payment_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@payment_router.patch("/{payment_id}", response_model=MemberPaymentRead)
async def update_payment(payment_id: int, data: MemberPaymentUpdate, user: CurrentUser, db: DBSession):
    payment = await service.get_payment_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
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


# ─── Fund Overview ─────────────────────────────────────────────────

@fund_router.get("/", response_model=GardenFundOverview)
async def get_fund_overview(
    user: CurrentUser,
    db: DBSession,
    year: int | None = Query(default=None),
):
    return await calculate_fund_overview(db, year=year)


# ─── Receipt Upload ───────────────────────────────────────────────

@receipt_router.post("/upload")
async def upload_receipt(user: CurrentUser, file: UploadFile = File(...)):
    """Upload a receipt image. Returns the file path for attaching to an expense or payment.

    ┌─────────────────────────────────────────────────────────────────┐
    │ KI-INTEGRATION (Phase 3):                                       │
    │                                                                  │
    │ Nach dem Upload kann ein OCR-Endpoint aufgerufen werden:         │
    │                                                                  │
    │   POST /api/finance/receipts/ocr                                │
    │   Body: { "image_path": "receipts/abc123.jpg" }                 │
    │   Response: {                                                    │
    │     "raw_text": "...",                                          │
    │     "suggested_amount_cents": 1299,                             │
    │     "suggested_description": "Baumarkt Erde 20L",              │
    │     "suggested_category": "Erde & Substrate",                   │
    │     "confidence": 0.87                                          │
    │   }                                                              │
    │                                                                  │
    │ Implementierung:                                                 │
    │ 1. Qwen-VL (empfohlen): Multimodal LLM, versteht Bilder       │
    │    - Model: Qwen/Qwen2-VL-7B-Instruct (lokal, ~16GB VRAM)     │
    │    - Prompt: "Extract total, store, items from receipt. JSON."  │
    │                                                                  │
    │ 2. PaddleOCR (Alternative): Reines OCR + Regex-Parsing         │
    │    - pip install paddleocr paddlepaddle                         │
    │                                                                  │
    │ 3. Integration:                                                  │
    │    - app/ocr/service.py → extract_receipt_data(image_path)      │
    │    - Frontend: Upload → OCR → Formular vorausgefüllt            │
    └─────────────────────────────────────────────────────────────────┘
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{file.content_type}' not allowed. Use JPEG, PNG, or WebP.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024} MB.",
        )

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}:
        ext = ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"

    receipt_dir = Path(settings.upload_dir) / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    file_path = receipt_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "path": f"receipts/{filename}",
        "size_bytes": len(content),
        "content_type": file.content_type,
    }


@receipt_router.get("/{filename}")
async def get_receipt(filename: str, user: CurrentUser):
    file_path = Path(settings.upload_dir) / "receipts" / filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return FileResponse(file_path)


standing_router = APIRouter(prefix="/api/finance/standing-orders", tags=["finance"])


# ─── Standing Orders ──────────────────────────────────────────────

@standing_router.get("/", response_model=list[StandingOrderRead])
async def list_standing_orders(
    user: CurrentUser, db: DBSession,
    user_id: int | None = Query(default=None),
):
    return await service.get_all_standing_orders(db, user_id=user_id)


@standing_router.post("/", response_model=StandingOrderRead, status_code=status.HTTP_201_CREATED)
async def create_standing_order(
    data: StandingOrderCreate, user: CurrentUser, db: DBSession
):
    """Create a standing order. Users create for themselves, admin can create for others."""
    target_user_id = data.user_id or user.id
    if target_user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admin can create standing orders for other users")
    order = await service.create_standing_order(db, target_user_id, data)
    await db.refresh(order)
    return order


@standing_router.patch("/{order_id}", response_model=StandingOrderRead)
async def update_standing_order(
    order_id: int, data: StandingOrderUpdate, user: CurrentUser, db: DBSession
):
    order = await service.get_standing_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Standing order not found")
    if order.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admin or owner can edit standing orders")
    updated = await service.update_standing_order(db, order, data)
    await db.refresh(updated)
    return updated


@standing_router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_standing_order(order_id: int, user: AdminUser, db: DBSession):
    order = await service.get_standing_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Standing order not found")
    await service.delete_standing_order(db, order)


@standing_router.post("/{order_id}/skip", response_model=StandingOrderSkipRead, status_code=status.HTTP_201_CREATED)
async def skip_month(order_id: int, data: StandingOrderSkipCreate, user: AdminUser, db: DBSession):
    """Admin marks a month as not paid for a standing order."""
    order = await service.get_standing_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Standing order not found")
    try:
        skip = await service.add_skip(db, order_id, data)
        return skip
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Month {data.year}-{data.month:02d} already skipped")


@standing_router.delete("/{order_id}/skip/{skip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unskip_month(order_id: int, skip_id: int, user: AdminUser, db: DBSession):
    """Admin removes a skip (marks month as paid again)."""
    await service.remove_skip(db, skip_id)

