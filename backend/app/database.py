import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger("gartenapp.database")

# ─── Engine Configuration ──────────────────────────────────────────

engine_kwargs: dict = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

if settings.is_sqlite:
    # SQLite: single writer, WAL mode
    engine_kwargs["connect_args"] = {"timeout": 30}
    engine_kwargs["pool_size"] = 1
    engine_kwargs["max_overflow"] = 0
else:
    # PostgreSQL: concurrent connections
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.async_database_url, **engine_kwargs)

# ─── SQLite Pragmas ────────────────────────────────────────────────

if settings.is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ─── Session Factory ──────────────────────────────────────────────

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─── Table Creation (debug / tests) ───────────────────────────────

async def create_all_tables() -> None:
    from app.audit import models as _audit  # noqa: F401
    from app.auth import models as _auth  # noqa: F401
    from app.beds import models as _beds  # noqa: F401
    from app.finance import models as _finance  # noqa: F401
    from app.garden import models as _garden  # noqa: F401
    from app.harvest import models as _harvest  # noqa: F401
    from app.messaging import models as _messaging  # noqa: F401
    from app.plants import models as _plants  # noqa: F401
    from app.watering import models as _watering  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ─── Dependency ────────────────────────────────────────────────────

async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Backward-compatible alias
get_async_session = get_db
