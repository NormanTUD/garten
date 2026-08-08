"""Append-only audit log with cryptographic hash chain.

The hash chain is opt-in: when enabled (settings.audit_hash_chain=True),
every audit entry stores the SHA-256 of the previous entry's content +
its own content, forming a tamper-evident sequence. Any modification of
historical rows breaks the chain and is detected by ``verify_chain()``.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.config import settings

logger = logging.getLogger("gartenapp.audit_chain")


def _serialize_for_hash(entry: AuditLog) -> str:
    payload = {
        "id": entry.id,
        "user_id": entry.user_id,
        "username": entry.username,
        "method": entry.method,
        "endpoint": entry.endpoint,
        "request_body": entry.request_body,
        "response_status": entry.response_status,
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "duration_ms": entry.duration_ms,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "prev_hash": entry.prev_hash or "",
    }
    return json.dumps(payload, sort_keys=True, default=str)


def compute_hash(entry: AuditLog) -> str:
    return hashlib.sha256(_serialize_for_hash(entry).encode("utf-8")).hexdigest()


async def get_last_entry(db: AsyncSession) -> AuditLog | None:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def append_with_chain(
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
) -> AuditLog:
    """Create an AuditLog row. If ``settings.audit_hash_chain`` is on,
    compute and persist ``entry_hash`` + ``prev_hash``.
    """
    if not settings.audit_hash_chain:
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
        return log

    last = await get_last_entry(db)
    prev_hash = last.entry_hash if last and last.entry_hash else None

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
        prev_hash=prev_hash,
    )
    db.add(log)
    await db.flush()
    log.entry_hash = compute_hash(log)
    await db.commit()
    return log


async def verify_chain(db: AsyncSession) -> tuple[bool, list[dict[str, Any]]]:
    """Walk the audit log and verify the hash chain. Returns
    ``(is_valid, breaks)`` where ``breaks`` is a list of dicts describing
    each broken entry."""
    result = await db.execute(select(AuditLog).order_by(AuditLog.id))
    rows = list(result.scalars().all())

    if not settings.audit_hash_chain:
        return True, []

    breaks: list[dict[str, Any]] = []
    prev_hash: str | None = None
    for row in rows:
        if row.prev_hash != prev_hash:
            breaks.append({
                "id": row.id,
                "reason": "prev_hash mismatch",
                "expected": prev_hash,
                "actual": row.prev_hash,
            })
        if row.entry_hash != compute_hash(row):
            breaks.append({
                "id": row.id,
                "reason": "entry_hash mismatch (content tampered)",
                "expected": compute_hash(row),
                "actual": row.entry_hash,
            })
        prev_hash = row.entry_hash
    return not breaks, breaks


async def export_csv(db: AsyncSession) -> str:
    """Dump every audit row as CSV. Useful for backups."""
    import csv
    import io

    result = await db.execute(select(AuditLog).order_by(AuditLog.id))
    rows = list(result.scalars().all())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "timestamp", "user_id", "username", "method",
        "endpoint", "response_status", "ip_address", "user_agent",
        "duration_ms", "request_body", "prev_hash", "entry_hash",
    ])
    for r in rows:
        writer.writerow([
            r.id, r.timestamp.isoformat() if r.timestamp else "",
            r.user_id or "", r.username or "", r.method,
            r.endpoint, r.response_status, r.ip_address or "",
            r.user_agent or "", r.duration_ms if r.duration_ms is not None else "",
            r.request_body or "", r.prev_hash or "", r.entry_hash or "",
        ])
    return buf.getvalue()
