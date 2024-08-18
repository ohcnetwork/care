from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from care.facility.api.serializers.encounter_symptom import EncounterSymptomSerializer
from care.facility.models.encounter_symptom import (
    ClinicalImpressionStatus,
    EncounterSymptom,
)
from care.utils.queryset.consultation import get_consultation_queryset


class EncounterSymptomFilter(filters.FilterSet):
    is_cured = filters.BooleanFilter(method="filter_is_cured")

    def filter_is_cured(self, queryset, name, value):
        if value:
            return queryset.filter(cure_date__isnull=False)
        return queryset.filter(cure_date__isnull=True)


class EncounterSymptomViewSet(ModelViewSet):
    serializer_class = EncounterSymptomSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = EncounterSymptom.objects.select_related("created_by", "updated_by")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = EncounterSymptomFilter
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

    def perform_destroy(self, instance):
        serializer = self.get_serializer(
            instance,
            data={
                "clinical_impression_status": ClinicalImpressionStatus.ENTERED_IN_ERROR
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
