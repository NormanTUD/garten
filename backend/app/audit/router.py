from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.audit import chain as audit_chain
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


@router.get("/chain/verify")
async def verify_audit_chain(admin: AdminUser, db: DBSession):
    """Verify the SHA-256 hash chain of the audit log.

    Returns ``{"valid": bool, "breaks": [...]}``. A non-empty ``breaks``
    list indicates that someone (or a bug) modified historical audit rows.
    """
    is_valid, breaks = await audit_chain.verify_chain(db)
    return JSONResponse(content={"valid": is_valid, "breaks": breaks})


@router.get("/export.csv", response_class=PlainTextResponse)
async def export_audit_csv(admin: AdminUser, db: DBSession):
    """Export the full audit log as CSV. Useful for off-site backups."""
    csv_text = await audit_chain.export_csv(db)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )

