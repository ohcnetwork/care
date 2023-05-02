from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.prescription import PrescriptionSerializer, MedicineAdministrationSerializer
from care.facility.models import Prescription, MedicineAdministration, DailyRound
from care.utils.queryset.consultation import get_consultation_queryset


class CommonPrescriptionViews():
    @action(methods=["POST"], detail=True)
    def administer(self, request, *args, **kwargs):
        prescription_obj = self.get_object()
        serializer = MedicineAdministrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(prescription=prescription_obj, administered_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=["GET"], detail=True)
    def get_administrations(self, request, *args, **kwargs):
        prescription_obj = self.get_object()
        serializer = MedicineAdministrationSerializer(
            MedicineAdministration.objects.filter(prescription_id=prescription_obj.id),
            many=True)
        return Response(serializer.data)

    # @action(methods=["DELETE"], detail=True)
    # def delete_administered(self, request, *args, **kwargs):
    #     if not request.query_params.get("id", None):
    #         return Response({"success": False, "error": "id is required"}, status=status.HTTP_400_BAD_REQUEST)
    #     administered_obj = MedicineAdministration.objects.get(external_id=request.query_params.get("id", None))
    #     administered_obj.delete()
    #     return Response({"success": True}, status=status.HTTP_200_OK)


class ConsultationPrescriptionViewSet(
    CommonPrescriptionViews,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = PrescriptionSerializer
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


class DailyRoundPrescriptionViewSet(
    CommonPrescriptionViews,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = PrescriptionSerializer
    permission_classes = (
        IsAuthenticated,
    )
    queryset = Prescription.objects.all().order_by("created_date")
    lookup_field = "external_id"

    def get_consultation_obj(self):
        daily_round = get_object_or_404(DailyRound.objects.filter(external_id=self.kwargs["daily_rounds_external_id"]))
        consultation = get_object_or_404(
            get_consultation_queryset(self.request.user).filter(id=daily_round.consultation_id))
        return daily_round, consultation

    def get_queryset(self):
        daily_round_obj, _ = self.get_consultation_obj()
        return self.queryset.filter(
            daily_round_id=daily_round_obj.id
        )

    def perform_create(self, serializer):
        daily_round_obj, _ = self.get_consultation_obj()
        serializer.save(prescribed_by=self.request.user, daily_round=daily_round_obj.id)
