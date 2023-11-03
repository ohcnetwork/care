from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.consultation_diagnosis import (
    ConsultationDiagnosisSerializer,
)
from care.facility.models import (
    ConditionVerificationStatus,
    ConsultationDiagnosis,
    generate_choices,
)
from care.utils.filters.choicefilter import CareChoiceFilter
from care.utils.queryset.consultation import get_consultation_queryset


class ConsultationDiagnosisFilter(filters.FilterSet):
    verification_status = CareChoiceFilter(
        choices=generate_choices(ConditionVerificationStatus)
    )


class ConsultationDiagnosisViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = ConsultationDiagnosisSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = (
        ConsultationDiagnosis.objects.all()
        .select_related("created_by")
        .order_by("-created_date")
    )
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

    def perform_create(self, serializer):
        consultation = self.get_consultation_obj()
        serializer.save(consultation=consultation, created_by=self.request.user)
