from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.audit.schemas import AuditLogQuery


async def create_audit_log(
    db: AsyncSession,
    *,
    user_id: int | None,
    username: str | None,
    method: str,
    endpoint: str,
    request_body: str | None,
    response_status: int,
    ip_address: str | None,
    user_agent: str | None,
    duration_ms: int | None,
) -> None:
    """Write an audit log entry. Called from middleware."""
    log = AuditLog(
        user_id=user_id,
        username=username,
        method=method,
        endpoint=endpoint,
        request_body=request_body,
        response_status=response_status,
        ip_address=ip_address,
        user_agent=user_agent,
        duration_ms=duration_ms,
    )
    db.add(log)
    await db.commit()


async def query_audit_logs(
    db: AsyncSession,
    query: AuditLogQuery,
) -> list[AuditLog]:
    """Query audit logs with optional filters."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if query.user_id is not None:
        stmt = stmt.where(AuditLog.user_id == query.user_id)
    if query.method is not None:
        stmt = stmt.where(AuditLog.method == query.method.upper())
    if query.endpoint_contains is not None:
        stmt = stmt.where(AuditLog.endpoint.contains(query.endpoint_contains))
    if query.status_min is not None:
        stmt = stmt.where(AuditLog.response_status >= query.status_min)
    if query.status_max is not None:
        stmt = stmt.where(AuditLog.response_status <= query.status_max)

    stmt = stmt.offset(query.offset).limit(query.limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_audit_log_count(db: AsyncSession) -> int:
    """Get total number of audit log entries."""
    result = await db.execute(select(AuditLog))
    return len(result.scalars().all())
