from care.emr.models.encounter import Encounter
from care.emr.reports.authorizers.discharge_summary import (
    DischargeSummaryReportAuthorizer,
)
from care.emr.reports.report_type_registry import ReportTypeRegistry

ReportTypeRegistry.register(
    key="discharge_summary",
    display_name="Discharge Summary",
    associating_model=Encounter,
    authorizer_class=DischargeSummaryReportAuthorizer,
    description="Discharge summary generated for an encounter",
)
