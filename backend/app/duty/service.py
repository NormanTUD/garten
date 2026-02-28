from datetime import date

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.duty.models import GardenDutyConfig, GardenDutyAssignment, GardenDutyLog
from app.duty.schemas import (
    DutyConfigCreate,
    DutyConfigUpdate,
    DutyAssignmentCreate,
    DutyAssignmentUpdate,
    DutyLogCreate,
    DutyMemberBalance,
    DutyOverview,
)


# ─── Config ────────────────────────────────────────────────

async def get_config(db: AsyncSession, year: int) -> GardenDutyConfig | None:
    result = await db.execute(
        select(GardenDutyConfig).where(GardenDutyConfig.year == year)
    )
    return result.scalar_one_or_none()


async def get_all_configs(db: AsyncSession) -> list[GardenDutyConfig]:
    result = await db.execute(
        select(GardenDutyConfig).order_by(GardenDutyConfig.year.desc())
    )
    return list(result.scalars().all())


async def create_config(db: AsyncSession, data: DutyConfigCreate) -> GardenDutyConfig:
    config = GardenDutyConfig(**data.model_dump())
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


async def update_config(
    db: AsyncSession, year: int, data: DutyConfigUpdate
) -> GardenDutyConfig | None:
    config = await get_config(db, year)
    if not config:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    await db.flush()
    await db.refresh(config)
    return config


async def delete_config(db: AsyncSession, year: int) -> bool:
    config = await get_config(db, year)
    if not config:
        return False
    await db.delete(config)
    return True


# ─── Assignments ───────────────────────────────────────────

async def get_assignments(db: AsyncSession, year: int) -> list[GardenDutyAssignment]:
    result = await db.execute(
        select(GardenDutyAssignment)
        .where(GardenDutyAssignment.year == year)
        .order_by(GardenDutyAssignment.user_id)
    )
    return list(result.scalars().all())


async def get_assignment(
    db: AsyncSession, user_id: int, year: int
) -> GardenDutyAssignment | None:
    result = await db.execute(
        select(GardenDutyAssignment)
        .where(GardenDutyAssignment.user_id == user_id)
        .where(GardenDutyAssignment.year == year)
    )
    return result.scalar_one_or_none()


async def create_assignment(
    db: AsyncSession, data: DutyAssignmentCreate
) -> GardenDutyAssignment:
    assignment = GardenDutyAssignment(**data.model_dump())
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def update_assignment(
    db: AsyncSession, assignment_id: int, data: DutyAssignmentUpdate
) -> GardenDutyAssignment | None:
    result = await db.execute(
        select(GardenDutyAssignment).where(GardenDutyAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def delete_assignment(db: AsyncSession, assignment_id: int) -> bool:
    result = await db.execute(
        select(GardenDutyAssignment).where(GardenDutyAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return False
    await db.delete(assignment)
    return True


async def auto_assign_equal(db: AsyncSession, year: int) -> list[GardenDutyAssignment]:
    """Auto-assign hours equally to all active members.
    Deletes existing assignments for that year first."""
    config = await get_config(db, year)
    if not config:
        raise ValueError(f"No duty config for year {year}")

    members_result = await db.execute(
        select(User).where(User.is_active.is_(True))
    )
    members = list(members_result.scalars().all())
    if not members:
        return []

    hours_per_member = round(config.total_hours / len(members), 2)

    # Delete existing assignments
    await db.execute(
        delete(GardenDutyAssignment).where(GardenDutyAssignment.year == year)
    )

    assignments = []
    for member in members:
        assignment = GardenDutyAssignment(
            user_id=member.id,
            year=year,
            assigned_hours=hours_per_member,
        )
        db.add(assignment)
        assignments.append(assignment)

    await db.flush()
    for a in assignments:
        await db.refresh(a)
    return assignments


# ─── Logs ──────────────────────────────────────────────────

async def get_logs(
    db: AsyncSession, year: int, user_id: int | None = None
) -> list[GardenDutyLog]:
    query = select(GardenDutyLog).where(
        func.extract("year", GardenDutyLog.date) == year
    )
    if user_id:
        query = query.where(GardenDutyLog.user_id == user_id)
    query = query.order_by(GardenDutyLog.date.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_log(
    db: AsyncSession, user_id: int, data: DutyLogCreate, is_admin: bool = False
) -> GardenDutyLog:
    log = GardenDutyLog(
        user_id=user_id,
        date=data.date,
        hours=data.hours,
        description=data.description,
        confirmed=is_admin,
        confirmed_by_id=user_id if is_admin else None,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def confirm_log(
    db: AsyncSession, log_id: int, admin_id: int
) -> GardenDutyLog | None:
    result = await db.execute(
        select(GardenDutyLog).where(GardenDutyLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        return None
    log.confirmed = True
    log.confirmed_by_id = admin_id
    await db.flush()
    await db.refresh(log)
    return log


async def unconfirm_log(db: AsyncSession, log_id: int) -> GardenDutyLog | None:
    result = await db.execute(
        select(GardenDutyLog).where(GardenDutyLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        return None
    log.confirmed = False
    log.confirmed_by_id = None
    await db.flush()
    await db.refresh(log)
    return log


async def delete_log(db: AsyncSession, log_id: int) -> bool:
    result = await db.execute(
        select(GardenDutyLog).where(GardenDutyLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        return False
    await db.delete(log)
    return True


# ─── Overview ──────────────────────────────────────────────

async def get_overview(db: AsyncSession, year: int) -> DutyOverview | None:
    config = await get_config(db, year)
    if not config:
        return None

    members_result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.display_name)
    )
    members = list(members_result.scalars().all())
    member_count = len(members) or 1

    assignments = await get_assignments(db, year)
    assignment_map = {a.user_id: a.assigned_hours for a in assignments}

    logs = await get_logs(db, year)

    # Group logs by user
    confirmed_map: dict[int, float] = {}
    pending_map: dict[int, float] = {}
    for log in logs:
        if log.confirmed:
            confirmed_map[log.user_id] = confirmed_map.get(log.user_id, 0) + log.hours
        else:
            pending_map[log.user_id] = pending_map.get(log.user_id, 0) + log.hours

    default_hours = round(config.total_hours / member_count, 2)
    total_assigned = sum(assignment_map.values())

    balances = []
    for member in members:
        assigned = assignment_map.get(member.id, default_hours)
        confirmed = confirmed_map.get(member.id, 0)
        pending = pending_map.get(member.id, 0)
        remaining = round(assigned - confirmed, 2)
        compensation = (
            round(remaining * config.hourly_rate_cents) if remaining > 0 else 0
        )

        balances.append(
            DutyMemberBalance(
                user_id=member.id,
                display_name=member.display_name,
                assigned_hours=assigned,
                confirmed_hours=confirmed,
                pending_hours=pending,
                remaining_hours=remaining,
                compensation_cents=compensation,
            )
        )

    return DutyOverview(
        year=year,
        total_hours=config.total_hours,
        hourly_rate_cents=config.hourly_rate_cents,
        total_assigned=total_assigned,
        total_unassigned=round(config.total_hours - total_assigned, 2),
        member_count=member_count,
        default_hours_per_member=default_hours,
        member_balances=balances,
    )

