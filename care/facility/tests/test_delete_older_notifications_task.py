from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from care.facility.models.notification import Notification
from care.facility.tasks.cleanup import delete_old_notifications


class DeleteOldNotificationsTest(TestCase):
    def test_delete_old_notifications(self):
        retention_days = settings.NOTIFICATION_RETENTION_DAYS

        # notifications created at the threshold of retention
        with freeze_time(timezone.now() - timedelta(days=retention_days)):
            notification1 = Notification.objects.create()
            notification2 = Notification.objects.create()

        # notification created now
        notification3 = Notification.objects.create()

        delete_old_notifications()

        # Assert
        self.assertFalse(Notification.objects.filter(pk=notification1.pk).exists())
        self.assertFalse(Notification.objects.filter(pk=notification2.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=notification3.pk).exists())
