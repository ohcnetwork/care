from django_filters import rest_framework as filters

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.fileupload import (
    FileUploadContextBuilder,
)
from care.emr.reports.context_builder.data_points.observation import (
    ObservationContextBuilder,
)


class ServiceRequestContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    title = Field(
        display="Title",
        preview_value="Blood Test Request",
        description="Title of the service request",
    )


class DiagnosticReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")


class DiagnosticReportContextBuilder(QuerysetContextBuilder):
    filterset_class = DiagnosticReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    def get_context(self):
        return DiagnosticReport.objects.filter(encounter=self.parent_context)

    title = Field(
        display="Title",
        preview_value="Chest X-Ray Report",
        description="Title of the diagnostic report",
        mapping=lambda dr: dr.code.get("display")
        if dr.code and dr.code.get("display")
        else "",
    )
    observations = Field(
        display="Observations",
        preview_value="",
        description="Observations summary included in the diagnostic report",
        target_context=ObservationContextBuilder,
    )
    conclusion = Field(
        display="Conclusion",
        preview_value="No abnormalities detected.",
        description="Conclusion of the diagnostic report",
    )
    note = Field(
        display="Notes",
        preview_value="Patient is in good health.",
        description="Additional notes regarding the diagnostic report",
    )

    service_request = Field(
        display="Service Request",
        preview_value="",
        description="Identifier for the associated service request",
        target_context=ServiceRequestContextBuilder,
    )

    file_uploads = Field(
        display="Uploaded Files",
        preview_value="",
        description="List of file uploads associated with the diagnostic report",
        target_context=FileUploadContextBuilder,
    )
