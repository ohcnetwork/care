from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.prescription import PrescriptionSerializer, MedicineAdministrationSerializer
from care.facility.models import Prescription
from care.utils.queryset.consultation import get_consultation_queryset


class PrescriptionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = PrescriptionSerializer
    serializer_action_classes = {
        "administer": MedicineAdministrationSerializer,
    }
    permission_classes = (
        IsAuthenticated,
    )
    queryset = Prescription.objects.all().order_by("created_date")
    lookup_field = "external_id"

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(external_id=self.kwargs["consultation_external_id"]))

    def get_queryset(self):
        consultation_obj = self.get_consultation_obj()
        return self.queryset.filter(
            consultation_id=consultation_obj.id
        )

    def perform_create(self, serializer):
        consultation_obj = self.get_consultation_obj()
        serializer.save(prescribed_by=self.request.user, consultation=consultation_obj)

    @action(methods=["POST"], detail=True)
    def administer(self, request, *args, **kwargs):
        prescription_obj = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(prescription=prescription_obj, administered_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @action(methods=["DELETE"], detail=True)
    # def delete_administered(self, request, *args, **kwargs):
    #     if not request.query_params.get("id", None):
    #         return Response({"success": False, "error": "id is required"}, status=status.HTTP_400_BAD_REQUEST)
    #     administered_obj = MedicineAdministration.objects.get(external_id=request.query_params.get("id", None))
    #     administered_obj.delete()
    #     return Response({"success": True}, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if hasattr(self, "serializer_action_classes"):
            if self.action in self.serializer_action_classes:
                return self.serializer_action_classes[self.action]
        return super().get_serializer_class()
