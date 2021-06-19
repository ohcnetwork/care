from django.db.models import F
from rest_framework import serializers


from care.facility.models.notification import Notification

from care.users.api.serializers.user import UserBaseMinimumSerializer
from config.serializers import ChoiceField


class NotificationSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    caused_by = UserBaseMinimumSerializer(read_only=True)

    event = ChoiceField(choices=Notification.EventChoices, read_only=True)
    event_type = ChoiceField(choices=Notification.EventTypeChoices, read_only=True)

    class Meta:
        model = Notification
        exclude = ("deleted", "modified_date", "intended_for", "medium_sent", "external_id")
        read_only_fields = (
            "message",
            "caused_objects",
            "created_date",
        )

