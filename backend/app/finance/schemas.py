from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Shared ────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str


# ─── Expense Category ─────────────────────────────────────────────

class ExpenseCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=50)


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class ExpenseCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    icon: str | None
    is_active: bool
    created_at: datetime


# ─── Expense Split ─────────────────────────────────────────────────

class ExpenseSplitInfo(BaseModel):
    """Used when creating an expense – specify who pays what."""
    user_id: int
    share_amount_cents: int = Field(..., ge=0)


class ExpenseSplitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    expense_id: int
    user_id: int
    user: UserSummary
    share_amount_cents: int
    is_settled: bool


# ─── Expense ───────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    category_id: int | None = None
    amount_cents: int = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    expense_date: date
    is_recurring: bool = False
    recurrence_interval: str | None = Field(
        default=None, pattern=r"^(monthly|quarterly|yearly)$"
    )
    notes: str | None = None
    splits: list[ExpenseSplitInfo] | None = None  # None = split equally among all active users


class ExpenseUpdate(BaseModel):
    category_id: int | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    expense_date: date | None = None
    is_recurring: bool | None = None
    recurrence_interval: str | None = Field(
        default=None, pattern=r"^(monthly|quarterly|yearly)$"
    )
    receipt_image_path: str | None = None
    notes: str | None = None


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    icon: str | None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    user: UserSummary
    category_id: int | None
    category: CategorySummary | None
    amount_cents: int
    description: str
    expense_date: date
    is_recurring: bool
    recurrence_interval: str | None
    notes: str | None
    splits: list[ExpenseSplitRead]
    created_at: datetime


# ─── Payment ───────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    to_user_id: int
    amount_cents: int = Field(..., gt=0)
    method: str = Field(default="cash", pattern=r"^(cash|transfer|material)$")
    description: str | None = Field(default=None, max_length=500)
    payment_date: date
    notes: str | None = None


class PaymentUpdate(BaseModel):
    amount_cents: int | None = Field(default=None, gt=0)
    method: str | None = Field(default=None, pattern=r"^(cash|transfer|material)$")
    description: str | None = Field(default=None, max_length=500)
    payment_date: date | None = None
    confirmed_by_admin: bool | None = None
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_user_id: int
    from_user: UserSummary
    to_user_id: int
    to_user: UserSummary
    amount_cents: int
    method: str
    description: str | None
    payment_date: date
    confirmed_by_admin: bool
    notes: str | None
    created_at: datetime


# ─── Balance ───────────────────────────────────────────────────────

class UserBalance(BaseModel):
    user_id: int
    display_name: str
    total_paid_cents: int       # How much this user paid for the group
    total_share_cents: int      # How much this user owes in total
    total_received_cents: int   # Payments received from others
    total_sent_cents: int       # Payments sent to others
    balance_cents: int          # Positive = others owe you, Negative = you owe others


class BalanceOverview(BaseModel):
    balances: list[UserBalance]
    total_expenses_cents: int

