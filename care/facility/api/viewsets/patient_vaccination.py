from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_vaccination import (
    PatientVaccineRegistrationSerializer,
)
from care.facility.models.patient_vaccination import VaccineRegistration


class VaccineRegistrationViewset(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    serializer_class = PatientVaccineRegistrationSerializer
    queryset = VaccineRegistration.objects.all()
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)
