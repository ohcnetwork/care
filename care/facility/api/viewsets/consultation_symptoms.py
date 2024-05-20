from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.consultation_symptom import (
    ConsultationSymptomSerializer,
)
from care.facility.models.consultation_symptom import ConsultationSymptom
from care.utils.queryset.consultation import get_consultation_queryset


class ConsultationSymptomFilter(filters.FilterSet):
    is_cured = filters.BooleanFilter(method="filter_is_cured")

    def filter_is_cured(self, queryset, name, value):
        if value:
            return queryset.filter(cure_date__isnull=False)
        return queryset.filter(cure_date__isnull=True)


class ConsultationSymptomViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = ConsultationSymptomSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = ConsultationSymptom.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ConsultationSymptomFilter
    lookup_field = "external_id"

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )

    def get_queryset(self):
        consultation = self.get_consultation_obj()
        return self.queryset.filter(consultation_id=consultation.id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["consultation"] = self.get_consultation_obj()
        return context
