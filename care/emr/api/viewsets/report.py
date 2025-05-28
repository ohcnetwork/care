from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRModelReadOnlyViewSet,
)
from care.emr.models import Encounter, Report
from care.emr.resources.report.spec import (
    ReportListSpec,
    ReportRetrieveSpec,
    ReportTypeChoices,
)
from care.security.authorization import AuthorizationController


def report_authorizer(user, file_type, associating_id, permission):
    allowed = False
    if file_type == ReportTypeChoices.discharge_summary.value:
        encounter_obj = get_object_or_404(Encounter, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, encounter_obj.patient
            ) or AuthorizationController.call(
                "can_view_encounter_obj", user, encounter_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_update_encounter_obj", user, encounter_obj
            )
    if not allowed:
        raise PermissionDenied("Cannot View Report")


class ReportFilter(filters.FilterSet):
    is_archived = filters.BooleanFilter(field_name="is_archived")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class ReportViewSet(EMRModelReadOnlyViewSet):
    database_model = Report
    pydantic_retrieve_model = ReportRetrieveSpec
    pydantic_read_model = ReportListSpec
    filterset_class = ReportFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        if self.action == "list":
            if (
                "file_type" not in self.request.GET
                and "associating_id" not in self.request.GET
            ):
                raise PermissionDenied("Cannot filter reports")
            report_authorizer(
                self.request.user,
                self.request.GET.get("file_type"),
                self.request.GET.get("associating_id"),
                "read",
            )
            return (
                super()
                .get_queryset()
                .filter(
                    file_type=self.request.GET.get("file_type"),
                    associating_id=self.request.GET.get("associating_id"),
                    upload_completed=True,
                )
            )
        obj = get_object_or_404(Report, external_id=self.kwargs["external_id"])
        report_authorizer(self.request.user, obj.file_type, obj.associating_id, "read")
        return super().get_queryset()

    class ArchiveRequestSpec(BaseModel):
        archive_reason: str

    @extend_schema(
        request=ArchiveRequestSpec,
        responses={200: ReportListSpec},
    )
    @action(detail=True, methods=["POST"])
    def archive(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_archived:
            raise ValidationError("This report is already archived.")
        request_data = self.ArchiveRequestSpec(**request.data)
        report_authorizer(request.user, obj.file_type, obj.associating_id, "write")
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
        return Response(ReportListSpec.serialize(obj).to_json())
