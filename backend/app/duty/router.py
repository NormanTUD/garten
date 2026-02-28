from fastapi import APIRouter, HTTPException, status

from app.dependencies import DBSession, CurrentUser, AdminUser
from app.duty import service
from app.duty.schemas import (
    DutyConfigCreate,
    DutyConfigRead,
    DutyConfigUpdate,
    DutyAssignmentCreate,
    DutyAssignmentRead,
    DutyAssignmentUpdate,
    DutyLogCreate,
    DutyLogRead,
    DutyOverview,
)

router = APIRouter(prefix="/duty", tags=["duty"])


# ─── Config (Admin only) ──────────────────────────────────

@router.get("/config", response_model=list[DutyConfigRead])
async def list_configs(user: CurrentUser, db: DBSession):
    return await service.get_all_configs(db)


@router.get("/config/{year}", response_model=DutyConfigRead)
async def get_config(year: int, user: CurrentUser, db: DBSession):
    config = await service.get_config(db, year)
    if not config:
        raise HTTPException(status_code=404, detail=f"No config for year {year}")
    return config


@router.post("/config", response_model=DutyConfigRead, status_code=status.HTTP_201_CREATED)
async def create_config(data: DutyConfigCreate, user: AdminUser, db: DBSession):
    existing = await service.get_config(db, data.year)
    if existing:
        raise HTTPException(status_code=409, detail=f"Config for {data.year} already exists")
    config = await service.create_config(db, data)
    await db.commit()
    return config


@router.put("/config/{year}", response_model=DutyConfigRead)
async def update_config(year: int, data: DutyConfigUpdate, user: AdminUser, db: DBSession):
    config = await service.update_config(db, year, data)
    if not config:
        raise HTTPException(status_code=404, detail=f"No config for year {year}")
    await db.commit()
    return config


@router.delete("/config/{year}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(year: int, user: AdminUser, db: DBSession):
    deleted = await service.delete_config(db, year)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No config for year {year}")
    await db.commit()


# ─── Assignments (Admin only) ─────────────────────────────

@router.get("/assignments/{year}", response_model=list[DutyAssignmentRead])
async def list_assignments(year: int, user: CurrentUser, db: DBSession):
    assignments = await service.get_assignments(db, year)
    return [DutyAssignmentRead.from_model(a) for a in assignments]


@router.post("/assignments", response_model=DutyAssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(data: DutyAssignmentCreate, user: AdminUser, db: DBSession):
    existing = await service.get_assignment(db, data.user_id, data.year)
    if existing:
        raise HTTPException(status_code=409, detail="Assignment already exists for this user/year")
    assignment = await service.create_assignment(db, data)
    await db.refresh(assignment)
    await db.commit()
    return DutyAssignmentRead.from_model(assignment)


@router.put("/assignments/{assignment_id}", response_model=DutyAssignmentRead)
async def update_assignment(
    assignment_id: int, data: DutyAssignmentUpdate, user: AdminUser, db: DBSession
):
    assignment = await service.update_assignment(db, assignment_id, data)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.commit()
    return DutyAssignmentRead.from_model(assignment)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(assignment_id: int, user: AdminUser, db: DBSession):
    deleted = await service.delete_assignment(db, assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.commit()


@router.post("/assignments/{year}/auto-assign", response_model=list[DutyAssignmentRead])
async def auto_assign(year: int, user: AdminUser, db: DBSession):
    try:
        assignments = await service.auto_assign_equal(db, year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return [DutyAssignmentRead.from_model(a) for a in assignments]


# ─── Logs ──────────────────────────────────────────────────

@router.get("/logs/{year}", response_model=list[DutyLogRead])
async def list_logs(year: int, user: CurrentUser, db: DBSession, user_id: int | None = None):
    logs = await service.get_logs(db, year, user_id=user_id)
    return [DutyLogRead.from_model(log) for log in logs]


@router.post("/logs", response_model=DutyLogRead, status_code=status.HTTP_201_CREATED)
async def create_log(data: DutyLogCreate, user: CurrentUser, db: DBSession):
    is_admin = user.role == "admin"
    log = await service.create_log(db, user.id, data, is_admin=is_admin)
    await db.refresh(log)
    await db.commit()
    return DutyLogRead.from_model(log)


@router.post("/logs/{log_id}/confirm", response_model=DutyLogRead)
async def confirm_log(log_id: int, user: AdminUser, db: DBSession):
    log = await service.confirm_log(db, log_id, user.id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    await db.commit()
    return DutyLogRead.from_model(log)


@router.post("/logs/{log_id}/unconfirm", response_model=DutyLogRead)
async def unconfirm_log(log_id: int, user: AdminUser, db: DBSession):
    log = await service.unconfirm_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    await db.commit()
    return DutyLogRead.from_model(log)


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(log_id: int, user: AdminUser, db: DBSession):
    deleted = await service.delete_log(db, log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log not found")
    await db.commit()


# ─── Overview ──────────────────────────────────────────────

@router.get("/overview/{year}", response_model=DutyOverview)
async def get_overview(year: int, user: CurrentUser, db: DBSession):
    overview = await service.get_overview(db, year)
    if not overview:
        raise HTTPException(
            status_code=404,
            detail=f"No duty config for year {year}. An admin needs to create one first.",
        )
    return overview

