from fastapi import APIRouter, Query

from app.audit.schemas import AuditLogQuery, AuditLogRead
from app.audit.service import get_audit_log_count, query_audit_logs
from app.dependencies import AdminUser, DBSession

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    admin: AdminUser,
    db: DBSession,
    user_id: int | None = Query(default=None),
    method: str | None = Query(default=None),
    endpoint_contains: str | None = Query(default=None),
    status_min: int | None = Query(default=None),
    status_max: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List audit logs with optional filters. Admin only."""
    query = AuditLogQuery(
        user_id=user_id,
        method=method,
        endpoint_contains=endpoint_contains,
        status_min=status_min,
        status_max=status_max,
        limit=limit,
        offset=offset,
    )
    return await query_audit_logs(db, query)


@router.get("/logs/count")
async def count_audit_logs(admin: AdminUser, db: DBSession):
    """Get total audit log count. Admin only."""
    count = await get_audit_log_count(db)
    return {"count": count}

