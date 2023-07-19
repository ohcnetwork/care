from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from care.facility.models.notification import Notification


@shared_task
def delete_old_notifications():
    ninety_days_ago = timezone.now() - timedelta(days=90)
    Notification.objects.filter(created_date__lte=ninety_days_ago).delete()
