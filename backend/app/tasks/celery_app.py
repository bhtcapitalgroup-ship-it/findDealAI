"""
RealDeal AI - Celery Application Configuration

Configures the Celery distributed task queue with Redis broker,
task routing, serialization settings, and beat schedule for periodic tasks.
"""

import os

from celery import Celery
from celery.schedules import crontab

# ---------------------------------------------------------------------------
# Broker / Backend configuration
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery("realdeal")

app.config_from_object(
    {
        # Broker
        "broker_url": REDIS_URL,
        "result_backend": RESULT_BACKEND,
        "broker_connection_retry_on_startup": True,
        # Serialization
        "accept_content": ["json"],
        "task_serializer": "json",
        "result_serializer": "json",
        "timezone": "US/Eastern",
        "enable_utc": True,
        # Task execution
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "worker_max_tasks_per_child": 200,
        "worker_concurrency": int(os.getenv("CELERY_CONCURRENCY", "4")),
        # Result expiry
        "result_expires": 60 * 60 * 24,  # 24 hours
        # Task time limits
        "task_soft_time_limit": 300,  # 5 minutes soft
        "task_time_limit": 600,  # 10 minutes hard
        # Rate limiting
        "worker_disable_rate_limits": False,
        # Task routing
        "task_routes": {
            "app.tasks.scraping_tasks.scrape_market": {"queue": "scraping"},
            "app.tasks.scraping_tasks.scrape_property_details": {"queue": "scraping"},
            "app.tasks.scraping_tasks.update_rent_estimates": {"queue": "scraping"},
            "app.tasks.scraping_tasks.refresh_market_data": {"queue": "scraping"},
            "app.tasks.scraping_tasks.daily_scrape_pipeline": {"queue": "scraping"},
            "app.tasks.analysis_tasks.analyze_property": {"queue": "analysis"},
            "app.tasks.analysis_tasks.batch_analyze_properties": {"queue": "analysis"},
            "app.tasks.analysis_tasks.check_alerts": {"queue": "alerts"},
            "app.tasks.analysis_tasks.update_investment_scores": {"queue": "analysis"},
        },
        "task_default_queue": "default",
        # Beat schedule (periodic tasks)
        "beat_schedule": {
            "daily-scrape-pipeline": {
                "task": "app.tasks.scraping_tasks.daily_scrape_pipeline",
                "schedule": crontab(hour=2, minute=0),  # 2:00 AM ET daily
                "options": {"queue": "scraping"},
            },
            "refresh-market-data": {
                "task": "app.tasks.scraping_tasks.refresh_market_data",
                "schedule": crontab(hour=4, minute=0),  # 4:00 AM ET daily
                "options": {"queue": "scraping"},
            },
            "update-rent-estimates": {
                "task": "app.tasks.scraping_tasks.update_rent_estimates",
                "schedule": crontab(hour=6, minute=0, day_of_week="monday"),  # Weekly
                "options": {"queue": "scraping"},
            },
            "check-alerts": {
                "task": "app.tasks.analysis_tasks.check_alerts",
                "schedule": crontab(minute="*/30"),  # Every 30 minutes
                "options": {"queue": "alerts"},
            },
            "update-investment-scores": {
                "task": "app.tasks.analysis_tasks.update_investment_scores",
                "schedule": crontab(hour=8, minute=0),  # 8:00 AM ET daily
                "options": {"queue": "analysis"},
            },
        },
    }
)

# Auto-discover tasks from these modules
app.autodiscover_tasks(
    [
        "app.tasks.scraping_tasks",
        "app.tasks.analysis_tasks",
    ]
)
