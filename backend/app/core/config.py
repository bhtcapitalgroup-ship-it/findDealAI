"""Application configuration using pydantic-settings.

All paid service keys have been removed or made optional.
The app runs on 100% free services by default.
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """RealDeal AI application settings.

    All values can be overridden via environment variables or a .env file
    located in the backend directory.

    FREE-TIER DEFAULTS:
    - Database: Neon free (or local PostgreSQL)
    - Redis: Upstash free (or local Redis)
    - AI: Template-based (or local Ollama)
    - Maps: Leaflet + OpenStreetMap (no API key)
    - Email: SendGrid free tier or Gmail SMTP
    - Scraping: Direct HTTP (no BrightData)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "RealDeal AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # -------------------------------------------------------------------------
    # Server
    # -------------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # -------------------------------------------------------------------------
    # Database  [FREE: Neon free tier  |  LOCAL: PostgreSQL 16]
    # -------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://realdeal:realdeal@localhost:5432/realdeal"

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to asyncpg format for SQLAlchemy async."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Strip sslmode param (asyncpg doesn't support it in URL)
        if "?sslmode=" in url:
            url = url.split("?sslmode=")[0]
        elif "&sslmode=" in url:
            url = url.replace("&sslmode=disable", "").replace("&sslmode=require", "")
        return url

    # -------------------------------------------------------------------------
    # Redis  [FREE: Upstash free tier  |  LOCAL: Redis 7]
    # -------------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # -------------------------------------------------------------------------
    # AI / LLM  [FREE: Template-based (no API)  |  OPTIONAL: Local Ollama]
    # -------------------------------------------------------------------------
    OLLAMA_URL: str = ""  # Empty = use template-based analysis (no LLM needed)
    OLLAMA_MODEL: str = "llama3"  # Model to use if Ollama is available

    # -------------------------------------------------------------------------
    # Scraping  [FREE: Direct HTTP with optional free proxies]
    # -------------------------------------------------------------------------
    FREE_PROXY_LIST: str = ""  # Optional comma-separated free proxy URLs

    # -------------------------------------------------------------------------
    # External Data APIs (Chrome Extension) -- free tiers available
    # -------------------------------------------------------------------------
    RENTCAST_API_KEY: str = ""
    CENSUS_API_KEY: str = ""  # FREE -- census.gov API keys are free
    GREATSCHOOLS_API_KEY: str = ""

    # -------------------------------------------------------------------------
    # Email  [FREE: SendGrid free tier (100/day) or Gmail SMTP]
    # -------------------------------------------------------------------------
    SENDGRID_API_KEY: str = ""  # FREE tier: 100 emails/day

    # SMTP fallback (Gmail SMTP is free with an app password)
    SMTP_HOST: str = ""  # e.g. "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # e.g. "you@gmail.com"
    SMTP_PASSWORD: str = ""  # Gmail app password (not your login password)

    NOTIFICATION_FROM_EMAIL: str = "alerts@realdeal-ai.com"
    NOTIFICATION_FROM_NAME: str = "RealDeal AI"

    # -------------------------------------------------------------------------
    # Auth / JWT
    # -------------------------------------------------------------------------
    JWT_SECRET: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # -------------------------------------------------------------------------
    # Stripe (optional -- only needed if accepting payments)
    # -------------------------------------------------------------------------
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # -------------------------------------------------------------------------
    # Sentry (optional -- free tier: 5K errors/month)
    # -------------------------------------------------------------------------
    SENTRY_DSN: str = ""

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://realdeal.ai",
        "https://app.realdeal.ai",
        "chrome-extension://*",
    ]

    # -------------------------------------------------------------------------
    # Rate limiting (requests per day by tier)
    # -------------------------------------------------------------------------
    RATE_LIMIT_FREE: int = 10
    RATE_LIMIT_PRO: int = 100
    RATE_LIMIT_PRO_PLUS: int = 1000

    # -------------------------------------------------------------------------
    # Celery  [Uses same Redis instance]
    # -------------------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"


settings = Settings()
