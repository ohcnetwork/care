from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from care.facility.api.serializers.patient_consultation import DailyRoundSerializer, PatientConsultationSerializer
from care.facility.models import DailyRound, PatientConsultation


class PatientConsultationViewSet(ModelViewSet):
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsultation.objects.all()


class DailyRoundsViewSet(ModelViewSet):
    serializer_class = DailyRoundSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = DailyRound.objects.all()

    def get_serializer(self, *args, **kwargs):
        try:
            kwargs["data"]["consultation"] = self.kwargs.get("consultation_pk")
        except KeyError:
            pass
        return super().get_serializer(*args, **kwargs)
