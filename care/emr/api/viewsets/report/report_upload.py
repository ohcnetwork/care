import logging

from django.utils import timezone
from django_filters import BooleanFilter, CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, ValidationError, field_validator, model_validator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports import report_utils
from care.emr.reports.authorizers import report_authorizer
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
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
from care.utils.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60


class ReportUploadFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template = CharFilter(field_name="template__slug", lookup_expr="exact")
    associating_id = CharFilter(field_name="associating_id", lookup_expr="exact")
    is_archived = BooleanFilter(field_name="is_archived")
    upload_completed = BooleanFilter(field_name="upload_completed")


class GenerateReportRequest(BaseModel):
    model_config = {"extra": "allow"}

    template_id: UUID4
    report_type: str = "discharge_summary"
    associating_id: UUID4
    output_format: str = "pdf"
    options: dict = {}

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v):
        valid_types = ReportTypeRegistry.get_all_keys()
        if v not in valid_types:
            msg = (
                f"Invalid report_type '{v}'. Valid types are: {', '.join(valid_types)}"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_report_type_and_associating_id(self):
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


class ReportUploadViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = ReportUpload
    pydantic_model = ReportUploadCreateSpec
    pydantic_read_model = ReportUploadListSpec
    pydantic_update_model = ReportUploadUpdateSpec
    pydantic_retrieve_model = ReportUploadRetrieveSpec

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReportUploadFilters
    ordering_fields = ["created_date", "name"]

    def get_queryset(self):
        if self.action == "list":
            if (
                "report_type" not in self.request.GET
                and "associating_id" not in self.request.GET
            ):
                raise PermissionError("Cannot filter Reports")

            report_authorizer(
                self.request.user,
                self.request.GET.get("report_type"),
                self.request.GET.get("associating_id"),
                "read",
            )
            return (
                super()
                .get_queryset()
                .filter(
                    report_type=self.request.GET.get("report_type"),
                    associating_id=self.request.GET.get("associating_id"),
                    upload_completed=True,
                )
            )
        obj = get_object_or_404(ReportUpload, external_id=self.kwargs["external_id"])
        report_authorizer(
            self.request.user, obj.report_type, obj.associating_id, "read"
        )
        return super().get_queryset()

    def authorize_create(self, instance):
        report_authorizer(
            self.request.user, instance.report_type, instance.associating_id, "write"
        )

    def authorize_update(self, request_obj, instance):
        report_authorizer(
            self.request.user, instance.report_type, instance.associating_id, "write"
        )

    @extend_schema(
        description="Get schema of available report types",
        responses={200: "Success"},
        tags=["report"],
    )
    @action(detail=False, methods=["GET"])
    def get_report_types(self, request, *args, **kwargs):
        try:
            schema = ReportTypeRegistry.get_schema()
            return Response(schema)
        except Exception as e:
            logger.exception("Failed to get report types schema: %s", e)
            return Response(
                {"error": "Failed to get report types"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(responses={200: ReportUploadListSpec})
    @action(detail=True, methods=["POST"])
    def mark_upload_completed(self, request, *args, **kwargs):
        obj = self.get_object()
        report_authorizer(request.user, obj.report_type, obj.associating_id, "write")
        obj.upload_completed = True
        obj.save(update_fields=["upload_completed"])
        return Response(ReportUploadListSpec.serialize(obj).to_json())

    @extend_schema(
        description="Generate a report from a template with patient/encounter data",
        request=GenerateReportRequest,
        responses={200: "Report generation started"},
        tags=["report"],
    )
    @action(detail=False, methods=["POST"])
    def generate(self, request, *args, **kwargs):  # noqa: PLR0911, PLR0912
        try:
            generate_request = GenerateReportRequest.model_validate(request.data)
        except ValidationError as e:
            errors = e.errors()
            if errors:
                error = errors[0]
                error_msg = error.get("msg", str(e))
                if "Value error," in error_msg:
                    error_msg = error_msg.replace("Value error, ", "")
                logger.warning("Validation error for report generation: %s", error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.exception("Validation error for report generation: %s", e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as e:
            logger.exception("Value error in report generation: %s", e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Unexpected error validating request data: %s", e)
            return Response(
                {"error": "Invalid request data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_id = str(generate_request.template_id)
        report_type = generate_request.report_type
        associating_id = str(generate_request.associating_id)

        extra_fields = {}
        for key, value in generate_request.model_dump(exclude_unset=True).items():
            if value is not None and key not in [
                "template_id",
                "associating_id",
                "report_type",
                "output_format",
                "options",
            ]:
                extra_fields[key] = str(value)

        output_format = generate_request.output_format.lower()

        report_authorizer(request.user, report_type, associating_id, "write")

        try:
            template = Template.objects.get(external_id=template_id)
        except Template.DoesNotExist:
            return Response(
                {"error": f"Template with id '{template_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if template.status != "active":
            return Response(
                {
                    "error": f"Template is not active (current status: {template.status})"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        context = DataPointRegistry.get(template.context)
        if not context:
            return Response(
                {"error": f"Invalid context '{template.context}' in template"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not GeneratorRegistry.is_registered(output_format):
            available_formats = ", ".join(GeneratorRegistry.get_all_formats())
            return Response(
                {
                    "error": f"Invalid output_format '{output_format}'. Available formats: {available_formats}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        lock_key = f"{report_type}_{associating_id}"
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
                output_format=output_format,
                options=generate_request.options,
                user_id=request.user.id,
                **extra_fields,
            )

            return Response(
                {
                    "detail": "Report generation started.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Failed to start report generation: %s", e)
            return Response(
                {"error": "Failed to start report generation"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    class ArchiveRequestSpec(BaseModel):
        archive_reason: str

    @extend_schema(request=ArchiveRequestSpec, responses={200: ReportUploadListSpec})
    @action(detail=True, methods=["POST"])
    def archive(self, request, *args, **kwargs):
        obj = self.get_object()
        request_data = self.ArchiveRequestSpec(**request.data)
        report_authorizer(request.user, obj.report_type, obj.associating_id, "write")
        obj.is_archived = True
        obj.archive_reason = request_data.archive_reason
        obj.archived_datetime = timezone.now()
        obj.archived_by = request.user
        obj.save(
            update_fields=[
                "is_archived",
                "archive_reason",
                "archived_datetime",
                "archived_by",
            ]
        )
        return Response(ReportUploadListSpec.serialize(obj).to_json())

    @extend_schema(
        description="Get download URL for the report",
        responses={200: "Download URL generated successfully"},
        tags=["report"],
    )
    @action(detail=True, methods=["GET"])
    def download(self, request, *args, **kwargs):
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
