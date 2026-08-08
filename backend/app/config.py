import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("gartenapp.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "GartenApp"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/gartenapp.db"

    # Auth
    secret_key: str = "change-me-to-a-random-secret-key-at-least-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # First admin (created on startup if no users exist)
    first_admin_username: str = "admin"
    first_admin_password: str = "change-me-on-first-login"

    # CORS
    cors_origins: str = "*"

    # File storage
    upload_dir: Path = Path("uploads")

    # Audit log
    audit_hash_chain: bool = True

    def model_post_init(self, __context) -> None:
        """Warn about insecure default secret_key in production."""
        if "change-me" in self.secret_key.lower() or len(self.secret_key) < 32:
            msg = (
                "SECRET_KEY is set to an insecure default or is too short. "
                "Generate a strong key with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
            if self.debug:
                logger.warning(msg)
            else:
                raise RuntimeError(msg)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def async_database_url(self) -> str:
        """Ensure the URL uses an async driver."""
        url = self.database_url
        if url.startswith("sqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
