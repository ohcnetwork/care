from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from care.facility.models.notification import Notification


@shared_task
def delete_old_notifications():
    retention_days = settings.NOTIFICATION_RETENTION_DAYS

    threshold_date = timezone.now() - timedelta(days=retention_days)
    Notification.objects.filter(created_date__lte=threshold_date).delete()
