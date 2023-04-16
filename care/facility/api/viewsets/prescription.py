from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from care.facility.models import Prescription, MedicineAdministration, PatientConsultation
from care.facility.api.serializers.prescription import PrescriptionSerializer, MedicineAdministrationSerializer
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated

class PrescriptionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = PrescriptionSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = Prescription.objects.all().order_by("-created_date")
    lookup_field = "external_id"

    def get_queryset(self):
        return self.queryset.filter(
            consultation__external_id=self.kwargs["consultation_external_id"]
        )
    
    def perform_create(self, serializer):

        consultation_obj = PatientConsultation.objects.get(external_id=self.kwargs["consultation_external_id"])

        serializer.save(prescribed_by=self.request.user, consultation=consultation_obj)
    
class MedicineAdministrationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = MedicineAdministrationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = MedicineAdministration.objects.all().order_by("-created_date")
    lookup_field = "external_id"

    def get_queryset(self):
        return self.queryset.filter(
            consultation__external_id=self.kwargs["consultation_external_id"]
        )