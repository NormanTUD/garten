from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── Shared ────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    icon: str | None


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


# ─── Recurring Cost ────────────────────────────────────────────────

class RecurringCostCreate(BaseModel):
    category_id: int | None = None
    description: str = Field(..., min_length=1, max_length=500)
    amount_cents: int = Field(..., gt=0)
    interval: str = Field(..., pattern=r"^(monthly|yearly)$")
    valid_from: date
    valid_to: date | None = None  # None = unbegrenzt
    notes: str | None = None


class RecurringCostUpdate(BaseModel):
    category_id: int | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    amount_cents: int | None = Field(default=None, gt=0)
    interval: str | None = Field(default=None, pattern=r"^(monthly|yearly)$")
    valid_from: date | None = None
    valid_to: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class RecurringCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int | None
    category: CategorySummary | None
    description: str
    amount_cents: int
    interval: str
    valid_from: date
    valid_to: date | None
    is_active: bool
    notes: str | None
    created_at: datetime


# ─── Garden Expense ────────────────────────────────────────────────

class GardenExpenseCreate(BaseModel):
    category_id: int | None = None
    category_name: str | None = None
    amount_cents: int = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    expense_date: date
    is_shared: bool = True  # NEU: auf alle umlegen?
    receipt_image_path: str | None = None
    notes: str | None = None


class GardenExpenseUpdate(BaseModel):
    category_id: int | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    expense_date: date | None = None
    is_shared: bool | None = None  # NEU
    receipt_image_path: str | None = None
    notes: str | None = None


class GardenExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    user: UserSummary
    category_id: int | None
    category: CategorySummary | None
    amount_cents: int
    description: str
    expense_date: date
    is_shared: bool
    confirmed_by_admin: bool
    confirmed_by_id: int | None
    receipt_image_path: str | None
    notes: str | None
    created_at: datetime


# ─── Member Payment ────────────────────────────────────────────────

class MemberPaymentCreate(BaseModel):
    amount_cents: int = Field(..., gt=0)
    payment_type: str = Field(..., pattern=r"^(cash|transfer|material)$")
    for_user_id: int | None = None  # NEU: Admin kann für anderen eintragen
    description: str | None = Field(default=None, max_length=500)
    payment_date: date
    receipt_image_path: str | None = None
    notes: str | None = None


class MemberPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    user: UserSummary
    for_user_id: int | None  # NEU
    for_user: UserSummary | None  # NEU
    amount_cents: int
    payment_type: str
    description: str | None
    payment_date: date
    receipt_image_path: str | None
    confirmed_by_admin: bool
    notes: str | None
    created_at: datetime

class MemberPaymentUpdate(BaseModel):
    amount_cents: int | None = Field(default=None, gt=0)
    payment_type: str | None = Field(default=None, pattern=r"^(cash|transfer|material)$")
    description: str | None = Field(default=None, max_length=500)
    payment_date: date | None = None
    receipt_image_path: str | None = None
    confirmed_by_admin: bool | None = None
    notes: str | None = None



# ─── Garden Fund Balance ───────────────────────────────────────────
class MemberBalance(BaseModel):
    user_id: int
    display_name: str
    total_paid_cents: int
    total_standing_order_cents: int       # Actual (completed months only)
    total_standing_order_projected_cents: int  # NEU: Full year projection
    total_income_cents: int               # Actual
    total_income_projected_cents: int     # NEU: Projected
    share_recurring_cents: int
    share_onetime_cents: int
    share_total_cents: int
    remaining_cents: int                  # Based on actual
    remaining_projected_cents: int        # NEU: Based on projected

class GardenFundOverview(BaseModel):
    # Laufende Kosten (projected = full year)
    total_recurring_monthly_cents: int
    total_recurring_yearly_cents: int
    total_recurring_annual_cents: int

    # Einmal-Ausgaben
    total_onetime_expenses_cents: int

    # Gesamt (projected)
    total_costs_annual_cents: int

    # Zahlungen (actual)
    total_payments_cents: int
    total_standing_order_cents: int           # Actual
    total_standing_order_projected_cents: int  # NEU
    total_income_cents: int                   # Actual
    total_income_projected_cents: int         # NEU
    fund_balance_cents: int

    # Pro Mitglied
    share_recurring_per_member_annual_cents: int
    share_recurring_per_member_monthly_cents: int
    share_onetime_per_member_cents: int
    share_total_per_member_annual_cents: int
    share_total_per_member_monthly_cents: int
    member_count: int
    member_balances: list[MemberBalance]


# ─── Standing Order ────────────────────────────────────────────────

class StandingOrderCreate(BaseModel):
    user_id: int | None = None  # None = self, admin can set for others
    amount_cents: int = Field(..., gt=0)
    description: str | None = Field(default=None, max_length=500)
    valid_from: date
    valid_to: date | None = None
    notes: str | None = None


class StandingOrderUpdate(BaseModel):
    amount_cents: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=500)
    valid_from: date | None = None
    valid_to: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class StandingOrderSkipCreate(BaseModel):
    year: int
    month: int = Field(..., ge=1, le=12)
    reason: str | None = Field(default=None, max_length=500)


class StandingOrderSkipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    standing_order_id: int
    year: int
    month: int
    reason: str | None


class StandingOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    user: UserSummary
    amount_cents: int
    description: str | None
    valid_from: date
    valid_to: date | None
    is_active: bool
    notes: str | None
    skips: list[StandingOrderSkipRead]
    created_at: datetime


class StandingOrderMonthStatus(BaseModel):
    """Status of a standing order for a specific month."""
    month: int
    month_name: str
    amount_cents: int
    is_paid: bool  # True unless skipped
    skip_reason: str | None = None


class StandingOrderYearSummary(BaseModel):
    """Summary of a standing order for a full year."""
    standing_order: StandingOrderRead
    months: list[StandingOrderMonthStatus]
    total_paid_cents: int
    total_skipped_cents: int
