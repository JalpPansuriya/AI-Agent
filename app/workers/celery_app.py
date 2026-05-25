from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.timezone = "UTC"

# Autodiscover tasks inside app.workers
celery_app.autodiscover_tasks(["app.workers"])

# Celery Beat schedules
celery_app.conf.beat_schedule = {
    "aggregate-daily-stats": {
        "task": "app.workers.tasks.aggregate_daily_stats",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    "cleanup-expired-tokens": {
        "task": "app.workers.tasks.cleanup_expired_tokens",
        "schedule": crontab(minute=0),  # Hourly at the start of every hour
    },
}
