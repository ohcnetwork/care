from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ReadOnlyModelViewSet

from care.facility.api.serializers.events import (
    EventTypeSerializer,
    NestedEventTypeSerializer,
    PatientConsultationEventDetailSerializer,
)
from care.facility.models.events import EventType, PatientConsultationEvent
from care.utils.queryset.consultation import get_consultation_queryset


class EventTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = EventTypeSerializer
    queryset = EventType.objects.filter(is_active=True)

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "roots":
            return NestedEventTypeSerializer
        return super().get_serializer_class()

    @extend_schema(tags=("event_types",))
    @method_decorator(cache_page(86400))
    @action(detail=True, methods=["GET"])
    def descendants(self, request, pk=None):
        event_type: EventType = get_object_or_404(self.queryset, pk=pk)
        queryset = self.get_queryset().filter(pk__in=event_type.get_descendants())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(tags=("event_types",))
    @method_decorator(cache_page(86400))
    @action(detail=False, methods=["GET"])
    def roots(self, request):
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PatientConsultationEventFilterSet(filters.FilterSet):
    ordering = filters.OrderingFilter(
        fields=(
            "created_date",
            "taken_at",
        )
    )

    class Meta:
        model = PatientConsultationEvent
        fields = [
            "event_type",
            "caused_by",
            "is_latest",
        ]


class PatientConsultationEventViewSet(ReadOnlyModelViewSet):
    serializer_class = PatientConsultationEventDetailSerializer
    queryset = PatientConsultationEvent.objects.all().select_related(
        "event_type", "caused_by"
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationEventFilterSet

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )

    def get_queryset(self):
        consultation = self.get_consultation_obj()
        return self.queryset.filter(consultation_id=consultation.id)
