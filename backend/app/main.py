import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory
from app.middleware.audit_log import AuditLogMiddleware

logger = logging.getLogger("gartenapp")

_scheduler_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task

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

    # Start the valve scheduler as a background task.
    from app.valves.scheduler import run_scheduler

    _scheduler_task = asyncio.create_task(run_scheduler(), name="valve-scheduler")

    yield

    if _scheduler_task is not None:
        _scheduler_task.cancel()
        import contextlib

        with contextlib.suppress(asyncio.CancelledError):
            await _scheduler_task
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
    from app.auth.apikeys.router import router as apikeys_router
    from app.auth.router import router as auth_router
    from app.auth.router import user_router
    from app.backup.router import router as backup_router
    from app.beds.router import planting_router
    from app.beds.router import router as beds_router
    from app.cameras.router import ingest_router as camera_ingest_router
    from app.cameras.router import router as cameras_router
    from app.devices.router import device_router as devices_device_router
    from app.devices.router import router as devices_router
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
    from app.network.router import router as network_router
    from app.plants.router import router as plants_router
    from app.shopping.router import router as shopping_router
    from app.timeline.router import router as timeline_router
    from app.valves.router import device_router as valves_device_router
    from app.valves.router import router as valves_router
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
    app.include_router(backup_router)
    app.include_router(apikeys_router)
    # New IoT / automation endpoints
    app.include_router(devices_router)
    app.include_router(devices_device_router)
    app.include_router(cameras_router)
    app.include_router(camera_ingest_router)
    app.include_router(network_router)
    app.include_router(valves_router)
    app.include_router(valves_device_router)
    app.include_router(timeline_router)

    @app.get("/api/health", tags=["system"])
    async def health_check():
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


app = create_app()

