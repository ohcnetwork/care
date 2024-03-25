from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "soft_delete": {
        "task": "care.facility.tasks.soft_delete_assets.soft_delete_assets_schedule",
        "schedule": crontab(minute=0, hour=0),
    },
}
