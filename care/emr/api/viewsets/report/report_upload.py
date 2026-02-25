import logging

from django.utils import timezone
from django_filters import BooleanFilter, CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, field_validator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports import report_utils
from care.emr.reports.authorizers import report_authorizer
from care.emr.reports.authorizers.utils import (
    read_report_authorizer,
    write_report_authorizer,
)
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.resources.report.report_upload.spec import (
    ReportUploadListSpec,
    ReportUploadRetrieveSpec,
)
from care.emr.tasks.report_generation import generate_report_task
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


class ReportUploadFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template = CharFilter(field_name="template__slug", lookup_expr="exact")
    associating_id = CharFilter(field_name="associating_id", lookup_expr="exact")
    is_archived = BooleanFilter(field_name="is_archived")
    upload_completed = BooleanFilter(field_name="upload_completed")


class GenerateReportRequest(BaseModel):
    template_id: UUID4
    associating_id: UUID4
    output_format: str | None = None
    force: bool = False
    status_check: bool = False

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v):
        if v and not GeneratorRegistry.is_registered(v):
            raise ValueError("Invalid output format")
        return v


class ReportUploadViewSet(EMRRetrieveMixin, EMRListMixin, EMRBaseViewSet):
    database_model = ReportUpload
    pydantic_read_model = ReportUploadListSpec
    pydantic_retrieve_model = ReportUploadRetrieveSpec

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReportUploadFilters
    ordering_fields = ["created_date", "name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            if (
                "report_type" not in self.request.GET
                or "associating_id" not in self.request.GET
            ):
                raise PermissionDenied("report_type and associating_id are required")
            report_type = self.request.GET.get("report_type")
            associating_id = self.request.GET.get("associating_id")
            read_report_authorizer(self.request.user, report_type, associating_id)
            return queryset.filter(
                report_type=report_type,
                associating_id=associating_id,
            )
        return queryset

    def authorize_retrieve(self, model_instance):
        read_report_authorizer(
            self.request.user,
            model_instance.report_type,
            model_instance.associating_id,
        )
        return super().authorize_retrieve(model_instance)

    def authorize_update(self, request_obj, model_instance):
        write_report_authorizer(
            self.request.user, model_instance.report_type, model_instance.associating_id
        )

    @extend_schema(
        description="Generate a report from a template with patient/encounter data",
        request=GenerateReportRequest,
        responses={201: "Report generation started"},
        tags=["report"],
    )
    @action(detail=False, methods=["POST"])
    def generate(self, request, *args, **kwargs):
        request_data = GenerateReportRequest.model_validate(request.data)

        template_id = request_data.template_id
        associating_id = request_data.associating_id

        template = get_object_or_404(Template, external_id=template_id)

        output_format = request_data.output_format or template.default_format

        report_authorizer(request.user, template.template_type, associating_id, "write")

        if template.facility and not AuthorizationController.call(
            "can_generate_report_from_template", request.user, template.facility
        ):
            raise PermissionDenied("You are not authorized to generate reports")

        if template.status != "active":
            raise ValidationError("Template is not active")

        lock_key = f"{template.template_type}_{associating_id}"

        if request_data.force:
            report_utils.clear_lock(lock_key)

        current_progress = report_utils.get_progress(lock_key)

        if request_data.status_check:
            if current_progress:
                return Response({"progress": current_progress})
            return Response({})

        if current_progress:
            return Response(
                {
                    "detail": (
                        f"Report generation is already in progress for this report, "
                        f"current progress {current_progress}%"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        generate_report_task.delay(
            template_id=template_id,
            report_type=template.template_type,
            associating_id=associating_id,
            output_format=output_format,
            user_id=request.user.id,
        )

        return Response(
            status=status.HTTP_201_CREATED,
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
