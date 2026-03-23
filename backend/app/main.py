"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Import all models so they register with Base.metadata
    import app.models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            "DB init failed (will retry on first request): %s", e
        )
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered property management platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers — skip optional modules that need extra deps
import importlib
_router_modules = [
    "auth", "properties", "units", "tenants", "leases", "payments",
    "maintenance", "contractors", "documents", "chat", "financials", "webhooks",
]
for mod_name in _router_modules:
    try:
        mod = importlib.import_module(f"app.api.v1.{mod_name}")
        app.include_router(mod.router, prefix="/api/v1")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Skipping router %s: %s", mod_name, e)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": settings.APP_VERSION}
