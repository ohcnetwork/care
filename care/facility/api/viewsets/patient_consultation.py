from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.file_upload import FileUploadRetrieveSerializer
from care.facility.api.serializers.patient_consultation import (
    EmailDischargeSummarySerializer,
    PatientConsultationDischargeSerializer,
    PatientConsultationIDSerializer,
    PatientConsultationSerializer,
)
from care.facility.api.viewsets.mixins.access import AssetUserAccessMixin
from care.facility.models.file_upload import FileUpload
from care.facility.models.mixins.permissions.asset import IsAssetUser
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.tasks.discharge_report import (
    email_discharge_summary,
    generate_and_upload_discharge_summary_task,
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
        elif self.action == "email_discharge_summary":
            return EmailDischargeSummarySerializer
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

    @extend_schema(tags=["consultation"])
    @action(detail=True, methods=["POST"])
    def discharge_patient(self, request, *args, **kwargs):
        consultation = self.get_object()
        serializer = self.get_serializer(consultation, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(current_bed=None)
        generate_and_upload_discharge_summary_task.delay(consultation.external_id)
        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        description="Generate a discharge summary",
        responses={
            200: "Success",
        },
        tags=["consultation"],
    )
    @action(detail=True, methods=["POST"])
    def generate_discharge_summary(self, request, *args, **kwargs):
        consultation = self.get_object()
        #  TODO : set a max discharge summary count for a consultation for a day/hour.
        generate_and_upload_discharge_summary_task.delay(consultation.external_id)
        return Response({})

    @extend_schema(
        description="Get the discharge summary",
        responses={200: "Success"},
        tags=["consultation"],
    )
    @action(detail=True, methods=["GET"])
    def preview_discharge_summary(self, request, *args, **kwargs):
        consultation = self.get_object()
        summary = (
            FileUpload.objects.filter(
                file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
                associating_id=consultation.external_id,
            )
            .order_by("-created_date")
            .first()
        )
        if summary and summary.upload_completed:
            return Response(FileUploadRetrieveSerializer(summary).data)
        raise NotFound(
            "Discharge summary is not ready yet. Please wait if a request has been placed."
        )

    @extend_schema(
        description="Email the discharge summary to the user",
        request=EmailDischargeSummarySerializer,
        responses={200: "Success"},
        tags=["consultation"],
    )
    @action(detail=True, methods=["POST"])
    def email_discharge_summary(self, request, *args, **kwargs):
        consultation = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        email_discharge_summary.delay(consultation.external_id, email)
        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: PatientConsultationIDSerializer}, tags=["consultation", "asset"]
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
