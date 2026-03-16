"""Structured logging configuration using structlog.

Produces JSON output in production and colored console output in development.
Integrates with uvicorn access logs and provides a performance timing processor.
"""

import logging
import sys
import time
from typing import Any

import structlog

from app.core.config import settings


def _add_timestamp(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO-8601 timestamp to every log entry."""
    # structlog.processors.TimeStamper handles this, but we keep it explicit
    return event_dict


def _add_app_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject application-level context into every log event."""
    event_dict.setdefault("app", settings.APP_NAME)
    event_dict.setdefault("environment", settings.ENVIRONMENT)
    return event_dict


class PerformanceTimingProcessor:
    """Structlog processor that measures elapsed time between bind and log call.

    Usage:
        log = structlog.get_logger().bind(_perf_start=time.perf_counter())
        # ... do work ...
        log.info("operation complete")  # duration_ms is added automatically
    """

    def __call__(
        self, logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        start = event_dict.pop("_perf_start", None)
        if start is not None:
            event_dict["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return event_dict


# ---------------------------------------------------------------------------
# Module-level log-level overrides
# ---------------------------------------------------------------------------
MODULE_LOG_LEVELS: dict[str, int] = {
    "uvicorn": logging.WARNING,
    "uvicorn.access": logging.INFO,
    "uvicorn.error": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
    "sqlalchemy.pool": logging.WARNING,
    "httpcore": logging.WARNING,
    "httpx": logging.WARNING,
    "celery": logging.INFO,
    "stripe": logging.INFO,
    "sentry_sdk": logging.WARNING,
}


def setup_logging() -> None:
    """Configure structlog and the stdlib logging bridge.

    Call this once at application startup (e.g. in the FastAPI lifespan).
    """
    is_production = settings.ENVIRONMENT == "production"
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # ------------------------------------------------------------------
    # Shared processors (used by both structlog and the stdlib bridge)
    # ------------------------------------------------------------------
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_app_context,
        PerformanceTimingProcessor(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        # JSON for production log aggregation (ELK, Datadog, etc.)
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Pretty console output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # ------------------------------------------------------------------
    # structlog configuration
    # ------------------------------------------------------------------
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ------------------------------------------------------------------
    # stdlib logging formatter powered by structlog
    # ------------------------------------------------------------------
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Root handler
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(root_handler)
    root_logger.setLevel(log_level)

    # Apply per-module overrides
    for module_name, level in MODULE_LOG_LEVELS.items():
        logging.getLogger(module_name).setLevel(level)

    # ------------------------------------------------------------------
    # Uvicorn access log integration
    # ------------------------------------------------------------------
    # Redirect uvicorn's access logger through structlog
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.addHandler(root_handler)
    uvicorn_access.propagate = False

    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers.clear()
    uvicorn_error.addHandler(root_handler)
    uvicorn_error.propagate = False


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger, optionally bound with a name.

    This is a thin convenience wrapper so callers do not need to import
    structlog directly.
    """
    log: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return log
