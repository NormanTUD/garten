import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger("gartenapp.database")

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={
        "timeout": 30,
    },
    pool_pre_ping=True,
    pool_size=1,        # SQLite: nur 1 Connection
    max_overflow=0,     # Keine zusätzlichen Connections
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode and busy timeout for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def create_all_tables() -> None:
    # Import all models so Base.metadata knows about them
    # Use module imports to avoid needing exact class names
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

