from django.contrib.auth import get_user_model
from rest_framework import serializers

from care.facility.models.notification import Notification
from care.users.api.serializers.user import UserBaseMinimumSerializer
from config.serializers import ChoiceField

User = get_user_model()

class NotificationListSerializer(serializers.ModelSerializer):
    event = ChoiceField(choices=Notification.EventChoices, read_only=True)
    id = serializers.UUIDField(source="external_id", read_only=True)
    caused_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "event", "caused_by", "message", "created_date", "read_at"]


class NotificationDetailSerializer(NotificationListSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    caused_by = UserBaseMinimumSerializer(read_only=True)

    event = ChoiceField(choices=Notification.EventChoices, read_only=True)
    event_type = ChoiceField(choices=Notification.EventTypeChoices, read_only=True)

    class Meta:
        model = Notification
        exclude = (
            "deleted",
            "modified_date",
            "intended_for",
            "medium_sent",
            "external_id",
        )
        read_only_fields = (
            "message",
            "caused_objects",
            "created_date",
        )
