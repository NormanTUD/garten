"""Service for full backups: database dump + media archive."""
from __future__ import annotations

import io
import logging
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings

logger = logging.getLogger("gartenapp.backup")


# Subdirectories of the upload dir that we want to include in backups.
MEDIA_SUBDIRS = ("camera_images", "camera_thumbs", "receipts")


def _is_sqlite_path() -> bool:
    return settings.database_url.startswith("sqlite")


def _resolve_sqlite_path() -> Path | None:
    """Extract the on-disk path from the SQLAlchemy URL."""
    url = settings.database_url
    if ":///" in url:
        path = url.split("///", 1)[1]
        return Path(path)
    return None


def build_backup_tarball() -> bytes:
    """Build a gzipped tar archive with the SQLite database + media files.

    Structure::

        backup-YYYYMMDD-HHMMSS/
        ├── gartenapp.db
        ├── media/
        │   ├── camera_images/...
        │   ├── camera_thumbs/...
        │   └── receipts/...
        └── manifest.json

    For non-SQLite databases (PostgreSQL) we just include a manifest – use
    ``pg_dump`` instead, which is what the production deployment runs.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    archive_root = f"backup-{timestamp}"

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        manifest = {
            "app": settings.app_name,
            "version": settings.app_version,
            "created_at": datetime.now(UTC).isoformat(),
            "database_kind": "sqlite" if _is_sqlite_path() else "postgresql",
            "media_subdirs": list(MEDIA_SUBDIRS),
        }

        # 1. Database file (SQLite only)
        if _is_sqlite_path():
            db_path = _resolve_sqlite_path()
            if db_path is not None and db_path.exists():
                tar.add(db_path, arcname=f"{archive_root}/gartenapp.db")
                manifest["database_size_bytes"] = db_path.stat().st_size
            else:
                logger.warning("SQLite DB file %s not found", db_path)

        # 2. Media directories
        for sub in MEDIA_SUBDIRS:
            media_dir = Path(settings.upload_dir) / sub
            if media_dir.exists():
                tar.add(
                    media_dir,
                    arcname=f"{archive_root}/media/{sub}",
                    recursive=True,
                )

        # 3. Manifest (always last so its size is deterministic)
        manifest_bytes = io.BytesIO(
            str(manifest).encode("utf-8")
        )
        info = tarfile.TarInfo(name=f"{archive_root}/manifest.json")
        info.size = len(manifest_bytes.getvalue())
        info.mtime = int(datetime.now(UTC).timestamp())
        tar.addfile(info, manifest_bytes)

    return buf.getvalue()


def restore_backup_tarball(data: bytes) -> dict:
    """Extract a backup tarball into ``upload_dir`` and replace the SQLite
    database. **Destructive**: overwrites the existing database file.

    Returns a dict describing what was restored.
    """
    result: dict = {
        "files_extracted": 0,
        "media_subdirs": [],
        "database_replaced": False,
    }
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = tar.getmembers()

        for member in members:
            if member.name.endswith("manifest.json"):
                continue
            # Refuse path traversal attempts
            if member.name.startswith("/") or ".." in member.name:
                logger.warning("Skipping unsafe member: %s", member.name)
                continue

            if member.name.endswith("gartenapp.db") and _is_sqlite_path():
                db_path = _resolve_sqlite_path()
                if db_path is None:
                    continue
                # Extract to a temp path then rename atomically
                tmp = db_path.with_suffix(db_path.suffix + ".new")
                f = tar.extractfile(member)
                if f is None:
                    continue
                tmp.write_bytes(f.read())
                tmp.replace(db_path)
                result["database_replaced"] = True
                continue

            # Media files
            if "/media/" in member.name and member.isreg():
                # 'data' filter rejects absolute paths / traversal automatically
                tar.extract(member, path=settings.upload_dir.parent, filter="data")
                result["files_extracted"] += 1
                sub = member.name.split("/media/", 1)[-1].split("/", 1)[0]
                if sub and sub not in result["media_subdirs"]:
                    result["media_subdirs"].append(sub)

    return result
