from datetime import timedelta

from celery.decorators import periodic_task
from celery.schedules import crontab
from django.utils import timezone

from care.facility.models.notification import Notification


@periodic_task(
    run_every=crontab(minute="0", hour="0")
)  # Run the task daily at midnight
def delete_old_notifications():
    ninety_days_ago = timezone.now() - timedelta(days=90)
    Notification.objects.filter(created_date__lte=ninety_days_ago).delete()
