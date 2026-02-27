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
    """Startup and shutdown logic."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    if settings.debug:
        await create_all_tables()
        logger.info("Database tables created (debug mode)")

    # Seed initial admin user
    from app.auth.service import ensure_admin_exists

    async with async_session_factory() as session:
        await ensure_admin_exists(
            session,
            settings.first_admin_username,
            settings.first_admin_password,
        )

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_app(
    audit_session_factory=None,
) -> FastAPI:
    """Application factory.

    Args:
        audit_session_factory: Optional session factory for audit middleware.
                               Used in tests to inject the test DB session.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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
    # Audit log middleware (outermost = runs first)
    app.add_middleware(AuditLogMiddleware, session_factory=audit_session_factory)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routers(app: FastAPI) -> None:
    """Register all API routers."""
    from app.audit.router import router as audit_router
    from app.auth.router import router as auth_router
    from app.auth.router import user_router

    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(audit_router)

    @app.get("/api/health", tags=["system"])
    async def health_check():
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }


app = create_app()

