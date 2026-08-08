import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory
from app.middleware.audit_log import AuditLogMiddleware

logger = logging.getLogger("gartenapp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    # Auto-create tables if missing (SQLite only, development-friendly).
    # For PostgreSQL, run `alembic upgrade head` before starting the app.
    await _ensure_schema()

    from app.auth.service import ensure_admin_exists
    from app.messaging.default_rules import seed_default_rules

    async with async_session_factory() as session:
        await ensure_admin_exists(session, settings.first_admin_username, settings.first_admin_password)
        await seed_default_rules(session)
        await session.commit()

    yield
    logger.info("Shutting down %s", settings.app_name)


async def _ensure_schema() -> None:
    """Create all tables if they do not yet exist.

    SQLite-friendly: tests/dev environments can boot without running
    Alembic manually. Alembic remains the source of truth for production
    migrations – run `alembic upgrade head` as part of your deploy.
    """
    from sqlalchemy import inspect, text

    from app.database import async_session_factory, create_all_tables, engine

    if settings.is_sqlite:
        async with engine.begin() as conn:
            tables_exist = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        if not tables_exist:
            logger.info("Empty database detected, creating tables...")
            await create_all_tables()
            return

    # For non-SQLite: try a cheap query to detect missing schema
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as err:
        logger.error(
            "Database not reachable or schema missing: %s. "
            "Run `alembic upgrade head` before starting the app.",
            err,
        )
        raise


def create_app(audit_session_factory=None) -> FastAPI:
    app = FastAPI(
        title=settings.app_name, version=settings.app_version,
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    setup_logging()
    setup_middleware(app, audit_session_factory=audit_session_factory)
    setup_routers(app)
    return app


def setup_logging() -> None:
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_middleware(app: FastAPI, audit_session_factory=None) -> None:
    app.add_middleware(AuditLogMiddleware, session_factory=audit_session_factory)
    cors_origins = settings.cors_origins_list
    allow_credentials = "*" not in cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routers(app: FastAPI) -> None:
    from app.audit.router import router as audit_router
    from app.auth.router import router as auth_router
    from app.auth.router import user_router
    from app.beds.router import planting_router
    from app.beds.router import router as beds_router
    from app.duty.router import router as duty_router
    from app.finance.router import (
        category_router,
        expense_router,
        fund_router,
        payment_router,
        receipt_router,
        recurring_router,
        standing_router,
    )
    from app.garden.router import router as garden_router
    from app.harvest.router import router as harvest_router
    from app.messaging.router import message_router, rule_router
    from app.plants.router import router as plants_router
    from app.shopping.router import router as shopping_router
    from app.watering.router import fertilizing_router, watering_router

    app.include_router(shopping_router)
    app.include_router(duty_router)
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(audit_router)
    app.include_router(garden_router)
    app.include_router(beds_router)
    app.include_router(planting_router)
    app.include_router(plants_router)
    app.include_router(harvest_router)
    app.include_router(watering_router)
    app.include_router(fertilizing_router)
    app.include_router(category_router)
    app.include_router(recurring_router)
    app.include_router(expense_router)
    app.include_router(payment_router)
    app.include_router(fund_router)
    app.include_router(receipt_router)
    app.include_router(standing_router)
    app.include_router(message_router)
    app.include_router(rule_router)

    @app.get("/api/health", tags=["system"])
    async def health_check():
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


app = create_app()

