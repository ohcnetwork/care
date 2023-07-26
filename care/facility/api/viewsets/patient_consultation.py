from celery import chord
from django.db.models import Prefetch
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
from care.facility.tasks.discharge_summary import (
    email_discharge_summary_task,
    generate_discharge_summary_task,
)
from care.facility.utils.reports import discharge_summary
from care.users.models import Skill, User
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
        if self.serializer_class == PatientConsultationSerializer:
            self.queryset = self.queryset.prefetch_related(
                "assigned_to",
                Prefetch(
                    "assigned_to__skills",
                    queryset=Skill.objects.filter(userskill__deleted=False),
                ),
            )
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
        discharge_summary.set_lock(consultation.external_id, 0)
        generate_discharge_summary_task.delay(consultation.external_id)
        return Response(status=status.HTTP_200_OK)

    def _generate_discharge_summary(self, consultation_ext_id: str):
        current_progress = discharge_summary.get_progress(consultation_ext_id)
        if current_progress:
            return Response(
                {
                    "detail": (
                        "Discharge Summary is already being generated, "
                        f"current progress {current_progress}%"
                    )
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        discharge_summary.set_lock(consultation_ext_id, 0)
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
            chord(generate_discharge_summary_task.s(consultation_ext_id))(
                email_discharge_summary_task.s([email])
            )
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
