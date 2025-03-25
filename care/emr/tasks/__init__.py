from celery import Celery, current_app
from celery.schedules import crontab

from care.emr.tasks.cleanup_expired_token_slots import cleanup_expired_token_slots


@current_app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    sender.add_periodic_task(
        crontab(hour="0", minute="0"),
        cleanup_expired_token_slots.s(),
        name="cleanup_expired_token_slots",
    )
