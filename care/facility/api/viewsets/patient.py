from django.db import transaction
from django.db.utils import IntegrityError
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.facility.api.mixins import UserAccessMixin
from care.facility.api.serializers.patient import (
    PatientAdmissionSerializer,
    PatientDetailSerializer,
    PatientSerializer,
)
from care.facility.models import PatientAdmission, PatientRegistration


class PatientFilterSet(filters.FilterSet):
    phone_number = filters.CharFilter(field_name="phone_number")


class PatientViewSet(UserAccessMixin, viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = PatientRegistration.objects.filter(deleted=False)
    serializer_class = PatientSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientFilterSet

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PatientDetailSerializer
        else:
            return self.serializer_class

    @action(detail=True, methods=["get"])
    def history(self, request, *args, **kwargs):
        user = request.user
        queryset = PatientAdmission.objects.filter(patient__id=self.kwargs.get("pk"))
        if not user.is_superuser:
            queryset = queryset.filter(patient__created_by=user)
        return Response(data=PatientAdmissionSerializer(queryset, many=True).data)


class PatientAdmissionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = PatientAdmission.objects.all()
    serializer_class = PatientAdmissionSerializer
    http_method_names = ["put", "delete", "get"]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(facility__id=self.kwargs.get("facility_pk"), is_active=True)
        if user.is_superuser:
            return queryset

        return queryset.filter(facility__created_by=user)

    def update(self, request, *args, **kwargs):
        data = {"facility_id": self.kwargs.get("facility_pk"), "patient_id": self.kwargs.get("pk")}
        admission_date = request.data.get("admission_date")
        if admission_date:
            data["admission_date"] = admission_date
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                PatientAdmission.objects.create(**serializer.validated_data)
        except IntegrityError:
            admitted_at = PatientAdmission.objects.get(
                patient_id=serializer.validated_data["patient_id"], is_active=True
            ).facility_id
            raise ValidationError(f"The patient is currenly admitted at facility {admitted_at}")
        return Response(status=204)

    def destroy(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data={
                "facility_id": self.kwargs.get("facility_pk"),
                "patient_id": self.kwargs.get("pk"),
                "discharge_date": request.data.get("discharge_date"),
            }
        )
        serializer.is_valid(raise_exception=True)
        discharge_date = serializer.validated_data.pop("discharge_date")
        admission = PatientAdmission.objects.filter(is_active=True, **serializer.validated_data)
        if not admission.exists():
            raise ValidationError(f"The patient is not admitted at facility {serializer.validated_data['facility_id']}")
        admission.update(discharge_date=discharge_date, is_active=False)
        return Response(status=204)
