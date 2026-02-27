from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    username: str | None
    method: str
    endpoint: str
    request_body: str | None
    response_status: int
    ip_address: str | None
    user_agent: str | None
    duration_ms: int | None
    timestamp: datetime


class AuditLogQuery(BaseModel):
    """Query parameters for filtering audit logs."""
    user_id: int | None = None
    method: str | None = None
    endpoint_contains: str | None = None
    status_min: int | None = None
    status_max: int | None = None
    limit: int = 100
    offset: int = 0

