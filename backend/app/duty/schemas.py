from datetime import date
from pydantic import BaseModel, Field


# ─── Config ────────────────────────────────────────────────

class DutyConfigCreate(BaseModel):
    year: int
    total_hours: float = Field(gt=0)
    hourly_rate_cents: int = Field(gt=0)
    notes: str | None = None


class DutyConfigUpdate(BaseModel):
    total_hours: float | None = Field(default=None, gt=0)
    hourly_rate_cents: int | None = Field(default=None, gt=0)
    notes: str | None = None


class DutyConfigRead(BaseModel):
    id: int
    year: int
    total_hours: float
    hourly_rate_cents: int
    notes: str | None

    model_config = {"from_attributes": True}


# ─── Assignment ────────────────────────────────────────────

class DutyAssignmentCreate(BaseModel):
    user_id: int
    year: int
    assigned_hours: float = Field(gt=0)
    notes: str | None = None


class DutyAssignmentUpdate(BaseModel):
    assigned_hours: float | None = Field(default=None, gt=0)
    notes: str | None = None


class DutyAssignmentRead(BaseModel):
    id: int
    user_id: int
    year: int
    assigned_hours: float
    notes: str | None
    display_name: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, obj):
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            year=obj.year,
            assigned_hours=obj.assigned_hours,
            notes=obj.notes,
            display_name=obj.user.display_name,
        )


# ─── Log ───────────────────────────────────────────────────

class DutyLogCreate(BaseModel):
    date: date
    hours: float = Field(gt=0)
    description: str | None = None

class DutyLogRead(BaseModel):
    id: int
    user_id: int
    date: date
    hours: float
    description: str
    confirmed: bool
    confirmed_by_id: int | None
    display_name: str
    confirmed_by_name: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, obj):
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            date=obj.date,
            hours=obj.hours,
            description=obj.description,
            confirmed=obj.confirmed,
            confirmed_by_id=obj.confirmed_by_id,
            display_name=obj.user.display_name,
            confirmed_by_name=obj.confirmed_by.display_name if obj.confirmed_by else None,
        )


# ─── Overview / Balance ───────────────────────────────────

class DutyMemberBalance(BaseModel):
    user_id: int
    display_name: str
    assigned_hours: float
    confirmed_hours: float
    pending_hours: float  # Logged but not yet confirmed
    remaining_hours: float  # assigned - confirmed (can be negative = extra)
    compensation_cents: int  # remaining_hours * hourly_rate (only if > 0)


class DutyOverview(BaseModel):
    year: int
    total_hours: float
    hourly_rate_cents: int
    total_assigned: float
    total_unassigned: float  # total_hours - sum(assigned)
    member_count: int
    default_hours_per_member: float
    member_balances: list[DutyMemberBalance]

