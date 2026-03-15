# Standard library
from typing import List

# Third-party
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    All required vars are validated at startup — app refuses to start if missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    APP_ENV: str = "development"        # development | staging | production
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str                 # required — no default

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str                   # required — no default

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str                 # required — no default
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    ALLOWED_ORIGINS: str = ""           # comma-separated; empty = allow all (dev)

    # ------------------------------------------------------------------
    # PDF Storage
    # ------------------------------------------------------------------
    PDF_STORAGE_PATH: str = "./storage/reports"

    # ------------------------------------------------------------------
    # Redis — POST-MVP
    # ------------------------------------------------------------------
    REDIS_URL: str | None = None

    # ------------------------------------------------------------------
    # Celery — POST-MVP
    # ------------------------------------------------------------------
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # ------------------------------------------------------------------
    # WhatsApp — POST-MVP (stubbed)
    # ------------------------------------------------------------------
    WHATSAPP_API_URL: str | None = None
    WHATSAPP_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origins(self) -> List[str]:
        """
        Returns list of allowed CORS origins.

        NOTE: Browsers block credentialed requests (Authorization header / cookies)
        when allow_origins=["*"] — explicit origins are required.
        Dev defaults cover the common React/Vite local ports.
        Override via ALLOWED_ORIGINS in .env for any other port.
        """
        if self.ALLOWED_ORIGINS:
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.is_development:
            # Explicit list — wildcard breaks credentialed browser requests
            return [
                "http://localhost:3000",   # Create React App
                "http://localhost:5173",   # Vite
                "http://localhost:4173",   # Vite preview
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        return []


# Singleton — import this everywhere
settings = Settings()
