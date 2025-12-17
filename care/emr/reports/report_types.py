from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.reports.authorizers.discharge_summary import (
    DischargeBillReportAuthorizer,
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
ReportTypeRegistry.register(
    key="patient_bill_summary",
    display_name="Discharge Bill",
    associating_model=Patient,
    authorizer_class=DischargeBillReportAuthorizer,
    description="Patient bill summary generated for a patient",
)
