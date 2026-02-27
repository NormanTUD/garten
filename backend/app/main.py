import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory, create_all_tables
from app.middleware.audit_log import AuditLogMiddleware

logger = logging.getLogger("gartenapp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    if settings.debug:
        await create_all_tables()
        logger.info("Database tables created (debug mode)")

    from app.auth.service import ensure_admin_exists
    from app.messaging.default_rules import seed_default_rules

    async with async_session_factory() as session:
        await ensure_admin_exists(session, settings.first_admin_username, settings.first_admin_password)
        await seed_default_rules(session)
        await session.commit()

    yield
    logger.info("Shutting down %s", settings.app_name)


def setup_logging() -> None:
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_middleware(app: FastAPI, audit_session_factory=None) -> None:
    app.add_middleware(AuditLogMiddleware, session_factory=audit_session_factory)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )


def setup_routers(app: FastAPI) -> None:
    from app.audit.router import router as audit_router
    from app.auth.router import router as auth_router
    from app.auth.router import user_router
    from app.beds.router import planting_router, router as beds_router
    from app.finance.router import (
        category_router, recurring_router, expense_router,
        payment_router, fund_router, receipt_router, standing_router,
    )
    from app.garden.router import router as garden_router
    from app.harvest.router import router as harvest_router
    from app.plants.router import router as plants_router
    from app.watering.router import fertilizing_router, watering_router
    from app.messaging.router import message_router, rule_router

    app.include_router(message_router)
    app.include_router(rule_router)
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

    @app.get("/api/health", tags=["system"])
    async def health_check():
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


app = create_app()

