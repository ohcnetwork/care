from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models import PatientConsultation


class PatientConsultationViewSet(ModelViewSet):
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsultation.objects.all()
