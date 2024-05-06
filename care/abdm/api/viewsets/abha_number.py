from django.db.models import Q
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.abha_number import AbhaNumberSerializer
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import HealthIdGateway
from care.utils.queryset.patient import get_patient_queryset


class AbhaNumberViewSet(
    GenericViewSet,
    RetrieveModelMixin,
):
    serializer_class = AbhaNumberSerializer
    model = AbhaNumber
    queryset = AbhaNumber.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        patients = get_patient_queryset(self.request.user)
        return queryset.filter(patient__in=patients, deleted=False)

    def get_object(self):
        queryset = self.get_queryset()
        id = self.kwargs.get("pk")

        instance = queryset.filter(
            Q(abha_number=id) | Q(health_id=id) | Q(patient__external_id=id)
        ).first()

        if not instance:
            raise Http404

        self.check_object_permissions(self.request, instance)

        return instance

    @action(detail=True, methods=["GET"])
    def qr_code(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        response = HealthIdGateway().get_qr_code(serializer.data)
        return Response(response)

    @action(detail=True, methods=["GET"])
    def profile(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        response = HealthIdGateway().get_profile(serializer.data)
        return Response(response)
