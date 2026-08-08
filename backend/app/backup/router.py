"""Backup / restore endpoints (admin only)."""
from __future__ import annotations

import tarfile

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.backup import service as backup_service
from app.dependencies import AdminUser

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/export")
async def export_backup(admin: AdminUser):
    """Download a gzipped tarball containing the SQLite database plus
    all media (camera images, thumbnails, receipts)."""
    payload = backup_service.build_backup_tarball()
    filename = f"gartenapp-backup-{payload[:8].hex()}.tar.gz"
    return Response(
        content=payload,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )


@router.post("/import")
async def import_backup(
    admin: AdminUser,
    file: UploadFile = File(...),
):
    """Restore a backup tarball. Destructive – overwrites the current DB."""
    data = await file.read()
    if not data:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Empty upload",
        )
    if len(data) > 500 * 1024 * 1024:  # 500 MB cap
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Backup file too large (>500 MB)",
        )
    try:
        result = backup_service.restore_backup_tarball(data)
    except tarfile.ReadError as err:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tarball: {err}",
        ) from err
    return result
