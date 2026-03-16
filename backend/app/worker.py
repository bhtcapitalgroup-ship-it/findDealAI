"""Celery application configuration and periodic beat schedule."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "realdeal",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="US/Eastern",
    enable_utc=True,

    # Task behaviour
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result expiry (24 hours)
    result_expires=86400,

    # Task routing
    task_default_queue="default",
    task_routes={
        "app.tasks.payment_tasks.*": {"queue": "payments"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
    },
)

# ---------------------------------------------------------------------------
# Auto-discover task modules
# ---------------------------------------------------------------------------

celery_app.autodiscover_tasks([
    "app.tasks.payment_tasks",
    "app.tasks.maintenance_tasks",
    "app.tasks.notification_tasks",
])

# ---------------------------------------------------------------------------
# Periodic beat schedule
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    # Daily at 9 AM ET — find leases with rent due today and send reminders
    "check_rent_due": {
        "task": "app.tasks.payment_tasks.check_rent_due",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "payments"},
    },

    # Daily at 10 AM ET — find overdue payments and send escalating reminders
    "check_late_payments": {
        "task": "app.tasks.payment_tasks.check_late_payments",
        "schedule": crontab(hour=10, minute=0),
        "options": {"queue": "payments"},
    },

    # Weekly on Monday at 8 AM ET — find leases expiring in 90/60/30 days
    "check_lease_expirations": {
        "task": "app.tasks.payment_tasks.check_lease_expirations",
        "schedule": crontab(hour=8, minute=0, day_of_week="monday"),
        "options": {"queue": "payments"},
    },

    # 1st of each month at 7 AM ET — generate monthly financial report
    "generate_monthly_report": {
        "task": "app.tasks.payment_tasks.generate_monthly_report",
        "schedule": crontab(hour=7, minute=0, day_of_month=1),
        "options": {"queue": "payments"},
    },
}
