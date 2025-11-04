from django.utils import timezone
from django_filters import BooleanFilter, CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, field_validator, model_validator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports import report_utils
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.report_type_registry import ReportTypeRegistry
from care.emr.reports.report_type_utils import validate_associating_id
from care.emr.resources.report.report_upload.spec import (
    ReportUploadCreateSpec,
    ReportUploadListSpec,
    ReportUploadRetrieveSpec,
    ReportUploadUpdateSpec,
)
from care.emr.tasks.report_generation import generate_report_task

LOCK_DURATION = 2 * 60


class ReportUploadFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template = CharFilter(field_name="template__slug", lookup_expr="exact")
    associating_id = CharFilter(field_name="associating_id", lookup_expr="exact")
    is_archived = BooleanFilter(field_name="is_archived")
    upload_completed = BooleanFilter(field_name="upload_completed")


class GenerateReportRequest(BaseModel):
    template_id: UUID4
    report_type: str = "discharge_summary"
    associating_id: UUID4
    patient_id: UUID4 | None = None
    encounter_id: UUID4 | None = None
    context_config: dict | None = None
    output_format: str = "pdf"
    options: dict = {}

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v):
        """Validate that report_type is registered"""
        valid_types = ReportTypeRegistry.get_all_keys()
        if v not in valid_types:
            msg = (
                f"Invalid report_type '{v}'. Valid types are: {', '.join(valid_types)}"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_report_type_and_associating_id(self):
        """Validate that associating_id matches the expected model for report_type"""
        try:
            config = ReportTypeRegistry.get(self.report_type)

            validate_associating_id(
                associating_model=config.associating_model,
                associating_id=str(self.associating_id),
                report_type_key=self.report_type,
            )
        except KeyError as e:
            raise ValueError(str(e)) from e
        except ValueError as e:
            raise ValueError(str(e)) from e

        return self


class ReportUploadViewSet(EMRModelViewSet):
    database_model = ReportUpload
    pydantic_model = ReportUploadCreateSpec
    pydantic_read_model = ReportUploadListSpec
    pydantic_update_model = ReportUploadUpdateSpec
    pydantic_retrieve_model = ReportUploadRetrieveSpec

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReportUploadFilters
    ordering_fields = ["created_date", "name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("include_archived") != "true":
            queryset = queryset.filter(is_archived=False)
        return queryset

    @extend_schema(
        description="Get schema of available report types",
        responses={200: "Success"},
        tags=["report"],
    )
    @action(detail=False, methods=["GET"])
    def get_report_types(self, request, *args, **kwargs):
        """Get all available report types with their configurations"""
        try:
            schema = ReportTypeRegistry.get_schema()
            return Response(schema)
        except Exception as e:
            return Response(
                {"error": f"Failed to get report types: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        description="Generate a report from a template with patient/encounter data",
        request=GenerateReportRequest,
        responses={200: "Report generation started"},
        tags=["report"],
    )
    @action(detail=False, methods=["POST"])
    def generate(self, request, *args, **kwargs):  # noqa: PLR0911
        try:
            generate_request = GenerateReportRequest.model_validate(request.data)
        except Exception as e:
            return Response(
                {"error": f"Invalid request data: {e!s}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_id = str(generate_request.template_id)
        report_type = generate_request.report_type
        associating_id = str(generate_request.associating_id)
        patient_id = (
            str(generate_request.patient_id) if generate_request.patient_id else None
        )
        encounter_id = (
            str(generate_request.encounter_id)
            if generate_request.encounter_id
            else None
        )
        output_format = generate_request.output_format.lower()

        # Validate template exists
        try:
            template = Template.objects.get(external_id=template_id)
        except Template.DoesNotExist:
            return Response(
                {"error": f"Template with id '{template_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check template status
        if template.status != "active":
            return Response(
                {
                    "error": f"Template is not active (current status: {template.status})"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        context_config = generate_request.context_config
        if context_config is None:
            context_config = template.context_config

        if not GeneratorRegistry.is_registered(output_format):
            available_formats = ", ".join(GeneratorRegistry.get_all_formats())
            return Response(
                {
                    "error": f"Invalid output_format '{output_format}'. Available formats: {available_formats}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        lock_key = f"{report_type}_report_{associating_id}"
        if current_progress := report_utils.get_progress(lock_key):
            return Response(
                {
                    "detail": (
                        f"Report generation is already in progress for this report, "
                        f"current progress {current_progress}%"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            generate_report_task.delay(
                template_id=template_id,
                report_type=report_type,
                associating_id=associating_id,
                patient_id=patient_id,
                encounter_id=encounter_id,
                context_config=context_config,
                output_format=output_format,
                options=generate_request.options,
            )

            return Response(
                {
                    "detail": "Report generation started. You will receive a notification when complete.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to start report generation: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        description="Archive a report", responses={200: "Success"}, tags=["report"]
    )
    @action(detail=True, methods=["POST"])
    def archive(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_archived:
            return Response(
                {"error": "Report is already archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        archive_reason = request.data.get("archive_reason", "")

        instance.is_archived = True
        instance.archive_reason = archive_reason
        instance.archived_by = request.user
        instance.archived_datetime = timezone.now()
        instance.save()

        data = self.pydantic_retrieve_model.serialize(instance, request.user).to_json()
        return Response(data)

    @extend_schema(
        description="Unarchive a report",
        responses={200: "Report unarchived successfully"},
        tags=["report"],
    )
    @action(detail=True, methods=["POST"])
    def unarchive(self, request, *args, **kwargs):
        """
        Unarchive a report.
        """
        instance = self.get_object()

        if not instance.is_archived:
            return Response(
                {"error": "Report is not archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.is_archived = False
        instance.archive_reason = ""
        instance.archived_by = None
        instance.archived_datetime = None
        instance.save()

        data = self.pydantic_retrieve_model.serialize(instance, request.user).to_json()
        return Response(data)

    @extend_schema(
        description="Get download URL for the report",
        responses={200: "Download URL generated successfully"},
        tags=["report"],
    )
    @action(detail=True, methods=["GET"])
    def download(self, request, *args, **kwargs):
        """
        Returns a signed URL
        """
        instance = self.get_object()

        if not instance.upload_completed:
            return Response(
                {"error": "Report upload not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            signed_url = instance.files_manager.read_signed_url(instance)

            return Response(
                {
                    "download_url": signed_url,
                    "file_name": instance.name,
                    "mime_type": instance.meta.get("mime_type"),
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to generate download URL: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
