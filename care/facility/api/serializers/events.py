from rest_framework.serializers import ModelSerializer

from care.facility.models.events import EventType, PatientConsultationEvent


class EventTypeSerializer(ModelSerializer):
    class Meta:
        model = EventType
        fields = "__all__"


class PatientConsultationEventDetailSerializer(ModelSerializer):
    class Meta:
        model = PatientConsultationEvent
        fields = "__all__"
