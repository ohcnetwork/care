from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from care.facility.api.serializers.events import (
    EventTypeSerializer,
    PatientConsultationEventDetailSerializer,
)
from care.facility.models.events import EventType, PatientConsultationEvent
from care.utils.queryset.consultation import get_consultation_queryset


class EventTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = EventTypeSerializer
    queryset = EventType.objects.all()
    permission_classes = (IsAuthenticated,)

    @action(detail=True, methods=["GET"])
    def descendants(self, request, pk=None):
        event_type: EventType = get_object_or_404(self.queryset, pk=pk)
        queryset = self.get_queryset().filter(pk__in=event_type.get_descendants())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PatientConsultationEventFilterSet(filters.FilterSet):
    class Meta:
        model = PatientConsultationEvent
        fields = {
            "event_type": ["exact"],
        }


class PatientConsultationEventViewSet(ReadOnlyModelViewSet):
    serializer_class = PatientConsultationEventDetailSerializer
    queryset = PatientConsultationEvent.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationEventFilterSet
    # lookup_field = "external_id"
    # lookup_url_kwarg = "external_id"

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )

    def get_queryset(self):
        consultation = self.get_consultation_obj()
        return self.queryset.filter(consultation_id=consultation.id)
