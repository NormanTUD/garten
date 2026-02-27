import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory, create_all_tables

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


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    setup_logging()
    setup_middleware(app)
    setup_routers(app)

    return app


def setup_logging() -> None:
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routers(app: FastAPI) -> None:
    """Register all API routers."""
    from app.auth.router import router as auth_router
    from app.auth.router import user_router

    app.include_router(auth_router)
    app.include_router(user_router)

    @app.get("/api/health", tags=["system"])
    async def health_check():
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }


app = create_app()
