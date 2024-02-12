from django_ulid.serializers import ULIDField
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from care.facility.models.events import EventType, PatientConsultationEvent


class EventTypeSerializer(ModelSerializer):
    class Meta:
        model = EventType
        fields = ("id", "parent", "name", "description", "model", "fields")


class NestedEventTypeSerializer(ModelSerializer):
    children = SerializerMethodField()

    class Meta:
        model = EventType
        fields = ("id", "parent", "name", "description", "model", "fields", "children")

    def get_children(self, obj: EventType) -> list[EventType] | None:
        return NestedEventTypeSerializer(obj.children.all(), many=True).data or None


class PatientConsultationEventDetailSerializer(ModelSerializer):
    id = ULIDField(source="external_id", read_only=True)
    event_type = EventTypeSerializer()

    class Meta:
        model = PatientConsultationEvent
        fields = "__all__"
