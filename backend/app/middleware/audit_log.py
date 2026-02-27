import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth.utils import TOKEN_TYPE_ACCESS, decode_token
from app.database import async_session_factory

logger = logging.getLogger("gartenapp.audit")

# Endpoints to skip logging (noisy / health checks)
SKIP_ENDPOINTS = {
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}

# Fields to mask in request body
SENSITIVE_FIELDS = {
    "password",
    "password_hash",
    "current_password",
    "new_password",
    "access_token",
    "refresh_token",
    "token",
    "secret",
}

# Max request body size to log (prevent huge payloads in DB)
MAX_BODY_LOG_SIZE = 10_000


def mask_sensitive_data(data: dict) -> dict:
    """Replace sensitive field values with '***'."""
    masked = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS:
            masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        else:
            masked[key] = value
    return masked


def extract_user_from_token(authorization: str | None) -> tuple[int | None, str | None]:
    """Try to extract user_id from Bearer token. Returns (user_id, None) or (None, None)."""
    if not authorization:
        return None, None
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, None
    payload = decode_token(parts[1])
    if payload is None or payload.get("type") != TOKEN_TYPE_ACCESS:
        return None, None
    try:
        return int(payload["sub"]), None
    except (KeyError, ValueError):
        return None, None


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip non-API and noisy endpoints
        path = request.url.path
        if path in SKIP_ENDPOINTS or not path.startswith("/api"):
            return await call_next(request)

        start_time = time.monotonic()

        # Read and parse request body
        request_body_str = None
        try:
            body_bytes = await request.body()
            if body_bytes and len(body_bytes) <= MAX_BODY_LOG_SIZE:
                try:
                    body_json = json.loads(body_bytes)
                    masked = mask_sensitive_data(body_json)
                    request_body_str = json.dumps(masked, ensure_ascii=False)
                except (json.JSONDecodeError, AttributeError):
                    request_body_str = "(non-JSON body)"
        except Exception:
            request_body_str = "(unreadable body)"

        # Extract user info from token (best-effort, before request processing)
        user_id, username = extract_user_from_token(
            request.headers.get("authorization")
        )

        # Process the request
        response = await call_next(request)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Write audit log asynchronously (separate session, won't affect request)
        try:
            from app.audit.service import create_audit_log

            async with async_session_factory() as session:
                await create_audit_log(
                    session,
                    user_id=user_id,
                    username=username,
                    method=request.method,
                    endpoint=path,
                    request_body=request_body_str,
                    response_status=response.status_code,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", "")[:500],
                    duration_ms=duration_ms,
                )
        except Exception:
            logger.exception("Failed to write audit log for %s %s", request.method, path)

        return response

