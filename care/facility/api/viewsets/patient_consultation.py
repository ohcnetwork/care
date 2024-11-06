import tempfile

from django.db import transaction
from django.db.models import Prefetch
from django.db.models.query_utils import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
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
    PatientConsentSerializer,
    PatientConsultationDischargeSerializer,
    PatientConsultationIDSerializer,
    PatientConsultationSerializer,
)
from care.facility.api.viewsets.mixins.access import AssetUserAccessMixin
from care.facility.models.bed import AssetBed, ConsultationBed
from care.facility.models.file_upload import FileUpload
from care.facility.models.mixins.permissions.asset import IsAssetUser
from care.facility.models.patient_consultation import (
    PatientConsent,
    PatientConsultation,
)
from care.facility.tasks.discharge_summary import (
    email_discharge_summary_task,
    generate_discharge_summary_task,
)
from care.facility.utils.reports import discharge_summary
from care.users.models import Skill, User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.queryset.consultation import get_consultation_queryset


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
        if self.action == "discharge_patient":
            return PatientConsultationDischargeSerializer
        if self.action == "email_discharge_summary":
            return EmailDischargeSummarySerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == "patient_from_asset":
            return (IsAssetUser(),)
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.serializer_class == PatientConsultationSerializer:
            queryset = queryset.prefetch_related(
                "assigned_to",
                Prefetch(
                    "assigned_to__skills",
                    queryset=Skill.objects.filter(userskill__deleted=False),
                ),
                "current_bed",
                "current_bed__bed",
                "current_bed__assets",
                "current_bed__assets__current_location",
            )
        if self.request.user.is_superuser:
            return queryset
        if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(patient__facility__state=self.request.user.state)
        if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return queryset.filter(
                patient__facility__district=self.request.user.district
            )
        allowed_facilities = get_accessible_facilities(self.request.user)
        # A user should be able to see all the consultations of a patient if the patient is active in an accessible facility
        applied_filters = Q(
            Q(patient__is_active=True) & Q(patient__facility__id__in=allowed_facilities)
        )
        # A user should be able to see all consultations part of their home facility
        applied_filters |= Q(facility=self.request.user.home_facility)
        return queryset.filter(applied_filters)

    @transaction.non_atomic_requests
    def create(self, request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["consultation"])
    @action(detail=True, methods=["POST"])
    def discharge_patient(self, request, *args, **kwargs):
        consultation = self.get_object()
        serializer = self.get_serializer(consultation, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(current_bed=None)
        discharge_summary.set_lock(consultation.external_id, 0)
        generate_discharge_summary_task.delay(consultation.external_id)
        return Response(status=status.HTTP_200_OK)

    def _generate_discharge_summary(self, consultation_ext_id: str):
        current_progress = discharge_summary.get_progress(consultation_ext_id)
        if current_progress is not None:
            return Response(
                {
                    "detail": (
                        "Discharge Summary is already being generated, "
                        f"current progress {current_progress}%"
                    )
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        discharge_summary.set_lock(consultation_ext_id, 1)
        generate_discharge_summary_task.delay(consultation_ext_id)
        return Response(
            {"detail": "Discharge Summary will be generated shortly"},
            status=status.HTTP_202_ACCEPTED,
        )

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
        if consultation.discharge_date:
            return Response(
                {
                    "detail": (
                        "Cannot generate a new discharge summary for already "
                        "discharged patient"
                    )
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        return self._generate_discharge_summary(consultation.external_id)

    @extend_schema(
        description="Get the discharge summary",
        responses={200: "Success"},
        tags=["consultation"],
    )
    @action(detail=True, methods=["GET"])
    def preview_discharge_summary(self, request, *args, **kwargs):
        consultation = self.get_object()
        summary_file = (
            FileUpload.objects.filter(
                file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
                associating_id=consultation.external_id,
                upload_completed=True,
            )
            .order_by("-created_date")
            .first()
        )
        if summary_file:
            return Response(FileUploadRetrieveSerializer(summary_file).data)
        return self._generate_discharge_summary(consultation.external_id)

    @extend_schema(
        description="Email the discharge summary to the user",
        request=EmailDischargeSummarySerializer,
        responses={200: "Success"},
        tags=["consultation"],
    )
    @action(detail=True, methods=["POST"])
    def email_discharge_summary(self, request, *args, **kwargs):
        consultation_ext_id = kwargs["external_id"]
        existing_progress = discharge_summary.get_progress(consultation_ext_id)
        if existing_progress:
            return Response(
                {
                    "detail": (
                        "Discharge Summary is already being generated, "
                        f"current progress {existing_progress}%"
                    )
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        summary_file = (
            FileUpload.objects.filter(
                file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
                associating_id=consultation_ext_id,
                upload_completed=True,
            )
            .order_by("-created_date")
            .first()
        )
        if not summary_file:
            (
                generate_discharge_summary_task.s(consultation_ext_id)
                | email_discharge_summary_task.s(emails=[email])
            ).delay()
        else:
            email_discharge_summary_task.delay(summary_file.id, [email])
        return Response(
            {"detail": "Discharge Summary will be emailed shortly"},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        responses={200: PatientConsultationIDSerializer}, tags=["consultation", "asset"]
    )
    @action(detail=False, methods=["GET"])
    def patient_from_asset(self, request):
        consultation_bed = (
            ConsultationBed.objects.filter(
                Q(assets=request.user.asset)
                | Q(bed__in=request.user.asset.bed_set.all()),
                end_date__isnull=True,
            )
            .order_by("-id")
            .first()
        )
        if not consultation_bed:
            raise NotFound({"detail": "No consultation bed found for this asset"})

        consultation = (
            PatientConsultation.objects.order_by("-id")
            .filter(
                current_bed=consultation_bed,
                patient__is_active=True,
            )
            .only("external_id", "patient__external_id")
            .first()
        )
        if not consultation:
            raise NotFound({"detail": "No consultation found for this asset"})

        asset_beds = []
        if preset_name := request.query_params.get("preset_name", None):
            asset_beds = AssetBed.objects.filter(
                asset__current_location=request.user.asset.current_location,
                bed=consultation_bed.bed,
                meta__preset_name__icontains=preset_name,
            ).select_related("bed", "asset")

        return Response(
            PatientConsultationIDSerializer(
                {
                    "patient_id": consultation.patient.external_id,
                    "consultation_id": consultation.external_id,
                    "bed_id": consultation_bed.bed.external_id,
                    "asset_beds": asset_beds,
                }
            ).data
        )


def dev_preview_discharge_summary(request, consultation_id):
    """
    This is a dev only view to preview the discharge summary template
    """
    consultation = (
        PatientConsultation.objects.select_related("patient")
        .order_by("-id")
        .filter(external_id=consultation_id)
        .first()
    )
    if not consultation:
        raise NotFound({"detail": "Consultation not found"})
    data = discharge_summary.get_discharge_summary_data(consultation)
    data["date"] = timezone.now()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        discharge_summary.generate_discharge_summary_pdf(data, tmp_file)
        tmp_file.seek(0)

        response = HttpResponse(tmp_file, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="discharge_summary.pdf"'

        return response


class PatientConsentViewSet(
    AssetUserAccessMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = PatientConsentSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsent.objects.all().select_related("consultation")
    filter_backends = (filters.DjangoFilterBackend,)

    filterset_fields = ("archived",)

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )

    def get_queryset(self):
        return self.queryset.filter(consultation=self.get_consultation_obj())

    def get_serializer_context(self):
        data = super().get_serializer_context()
        data["consultation"] = self.get_consultation_obj()
        return data
