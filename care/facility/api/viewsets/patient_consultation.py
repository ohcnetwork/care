from rest_framework.mixins import ListModelMixin

from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import PatientConsultation


class PatientConsultationViewSet(FacilityBaseViewset, ListModelMixin):
    serializer_class = PatientConsultationSerializer
    queryset = PatientConsultation.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(facility__id=self.kwargs.get("facility_pk"))
        if user.is_superuser:
            return queryset
        return queryset.filter(facility__created_by=user)

    def get_serializer(self, *args, **kwargs):
        try:
            kwargs["data"]["facility"] = self.kwargs.get("facility_pk")
        except KeyError:
            pass
        return super().get_serializer(*args, **kwargs)

    def destroy(self):
        raise NotImplementedError()
