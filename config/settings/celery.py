import os

from celery.schedules import crontab

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")

CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "Asia/Shanghai"

CELERY_TASK_TIME_LIMIT = 30

CELERY_TASK_SOFT_TIME_LIMIT = 20

CELERY_TASK_ACKS_LATE = True

CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_TASK_DEFAULT_RETRY_DELAY = 60

CELERY_TASK_MAX_RETRIES = 3

CELERY_BEAT_SCHEDULE = {
    "daily-calendar-sync": {
        "task": "apps.sync.tasks.calendar.sync_calendar_task",
        "schedule": crontab(
            hour=os.getenv("SYNC_CALENDAR_CRON_HOUR", "3"),
            minute=os.getenv("SYNC_CALENDAR_CRON_MINUTE", "30"),
        ),
    },
    "daily-incremental-sync": {
        "task": "apps.sync.tasks.incremental.run_incremental_sync_task",
        "schedule": crontab(
            hour=os.getenv("SYNC_INCREMENTAL_CRON_HOUR", "4"),
            minute=os.getenv("SYNC_INCREMENTAL_CRON_MINUTE", "0"),
        ),
    },
}
