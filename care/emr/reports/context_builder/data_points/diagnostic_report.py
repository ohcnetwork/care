from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.observation import (
    ObservationContextBuilder,
)


class DiagnosticReportContextBuilder(QuerysetContextBuilder):
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
