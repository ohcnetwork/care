from django.shortcuts import get_object_or_404
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_consultation import (
    ConsultationSymptomsSerializers,
)
from care.facility.models.consultation_symptom import ConsultationSymptom
from care.utils.queryset.consultation import get_consultation_queryset


class ConsultationSymptomsViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = ConsultationSymptomsSerializers
    permission_classes = [IsAuthenticated, DRYPermissions]
    queryset = ConsultationSymptom.objects.all()
    lookup_field = "external_id"

    def get_queryset(self):
        consultation = get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )
        return self.queryset.filter(consultation=consultation, cure_date__isnull=True)
