from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from care.facility.api.serializers.patient_consultation import DailyRoundSerializer, PatientConsultationSerializer
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from care.users.models import User


class PatientConsultationFilter(filters.FilterSet):
    patient = filters.NumberFilter(field_name="patient_id")
    facility = filters.NumberFilter(field_name="facility_id")


class PatientConsultationViewSet(ModelViewSet):
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsultation.objects.all().select_related("facility").order_by("-id")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationFilter

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(patient__district=self.request.user.district)
        return self.queryset.filter(facility__created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        Consultation List

        Supported filters
        - `facility` - ID
        - `patient` - ID
        """
        return super().list(request, *args, **kwargs)


class DailyRoundsViewSet(ModelViewSet):
    serializer_class = DailyRoundSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = DailyRound.objects.all().order_by("-id")

    def get_queryset(self):
        queryset = self.queryset.filter(consultation_id=self.kwargs.get("consultation_pk"))
        return queryset

    def get_serializer(self, *args, **kwargs):
        try:
            kwargs["data"]["consultation"] = self.kwargs.get("consultation_pk")
        except KeyError:
            pass
        return super().get_serializer(*args, **kwargs)
