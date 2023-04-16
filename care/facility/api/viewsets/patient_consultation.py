import time
from datetime import timedelta

from django.core.validators import validate_email
from django.db.models.query_utils import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.file_upload import FileUploadRetrieveSerializer
from care.facility.api.serializers.patient_consultation import (
    PatientConsultationDischargeSerializer,
    PatientConsultationIDSerializer,
    PatientConsultationSerializer,
)
from care.facility.api.viewsets.mixins.access import AssetUserAccessMixin
from care.facility.models.file_upload import FileUpload
from care.facility.models.mixins.permissions.asset import IsAssetUser
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.tasks.patient.discharge_report import (
    email_discharge_summary,
    generate_and_upload_discharge_summary,
)
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class PatientConsultationFilter(filters.FilterSet):
    patient = filters.CharFilter(field_name="patient__external_id")
    facility = filters.NumberFilter(field_name="facility_id")


class PatientConsultationViewSet(
    AssetUserAccessMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = (
        PatientConsultation.objects.all().select_related("facility").order_by("-id")
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationFilter

    def get_serializer_class(self):
        if self.action == "patient_from_asset":
            return PatientConsultationIDSerializer
        elif self.action == "discharge_patient":
            return PatientConsultationDischargeSerializer
        else:
            return self.serializer_class

    def get_permissions(self):
        if self.action == "patient_from_asset":
            return (IsAssetUser(),)
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(
                patient__facility__state=self.request.user.state
            )
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(
                patient__facility__district=self.request.user.district
            )
        allowed_facilities = get_accessible_facilities(self.request.user)
        applied_filters = Q(patient__facility__id__in=allowed_facilities)
        applied_filters |= Q(assigned_to=self.request.user)
        applied_filters |= Q(patient__assigned_to=self.request.user)
        return self.queryset.filter(applied_filters)

    @action(detail=True, methods=["POST"])
    def discharge_patient(self, request, *args, **kwargs):
        consultation = self.get_object()
        serializer = self.get_serializer(consultation, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        generate_and_upload_discharge_summary.delay(consultation.external_id)
        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get the discharge summary",
        responses={
            200: "Success",
        },
    )
    @action(detail=True, methods=["GET"])
    def preview_discharge_summary(self, request, *args, **kwargs):
        consultation = self.get_object()
        file = (
            FileUpload.objects.filter(
                file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
                associating_id=consultation.external_id,
            )
            .order_by("-created_date")
            .first()
        )
        if file is not None and file.upload_completed:
            return Response(FileUploadRetrieveSerializer(file).data)

        if file.created_date <= timezone.now() - timedelta(minutes=10):
            # If the file is not uploaded in 10 minutes, delete the file and generate a new one
            file.delete()
            file = None

        if file is None:
            generate_and_upload_discharge_summary.delay(consultation.external_id)
            time.sleep(2)  # Wait for 2 seconds for the file to be generated

        raise Response(
            {
                "message": "Discharge summary is not ready yet. Please try again after a few moments."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    @swagger_auto_schema(
        operation_description="Email the discharge summary to the user",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Email address"
                )
            },
            required=["email"],
        ),
        responses={200: "Success"},
    )
    @action(detail=True, methods=["POST"])
    def email_discharge_summary(self, request, *args, **kwargs):
        consultation = self.get_object()
        email = request.data.get("email", "")
        try:
            validate_email(email)
        except Exception:
            email = request.user.email

        email_discharge_summary.delay(consultation.external_id, email)
        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(
        responses={200: PatientConsultationIDSerializer},
    )
    @action(detail=False, methods=["GET"])
    def patient_from_asset(self, request):
        consultation = (
            PatientConsultation.objects.select_related("patient")
            .order_by("-id")
            .filter(
                current_bed__bed__in=request.user.asset.bed_set.all(),
                patient__is_active=True,
            )
            .only("external_id", "patient__external_id")
            .first()
        )
        if not consultation:
            raise NotFound({"detail": "No consultation found for this asset"})
        return Response(PatientConsultationIDSerializer(consultation).data)
