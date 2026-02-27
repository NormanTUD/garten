import logging

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger("gartenapp.database")

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={
        "timeout": 30,  # Wait up to 30s for locks
    },
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode and busy timeout for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Import Base from a separate module to avoid circular imports
from sqlalchemy.orm import DeclarativeBase  # noqa: E402


class Base(DeclarativeBase):
    pass


async def create_all_tables() -> None:
    from app.audit.models import AuditLog  # noqa: F401
    from app.auth.models import User  # noqa: F401
    from app.beds.models import Bed, Planting  # noqa: F401
    from app.finance.models import (  # noqa: F401
        ExpenseCategory,
        GardenExpense,
        MemberPayment,
        RecurringCost,
        StandingOrder,
        StandingOrderSkip,
    )
    from app.garden.models import Garden  # noqa: F401
    from app.harvest.models import Harvest  # noqa: F401
    from app.messaging.models import AutoMessageRule, Message  # noqa: F401
    from app.plants.models import Plant  # noqa: F401
    from app.watering.models import FertilizingLog, WateringLog  # noqa: F401

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

get_async_session = get_db
