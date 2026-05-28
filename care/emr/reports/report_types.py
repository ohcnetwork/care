from care.emr.models.account import Account
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.reports.authorizers.account import AccountReportAuthorizer
from care.emr.reports.authorizers.discharge_summary import (
    DischargeSummaryReportAuthorizer,
)
from care.emr.reports.authorizers.encounter import EncounterReportAuthorizer
from care.emr.reports.authorizers.patient import PatientReportAuthorizer
from care.emr.reports.report_type_registry import ReportTypeRegistry

ReportTypeRegistry.register(
    key="discharge_summary",
    display_name="Discharge Summary",
    associating_model=Encounter,
    authorizer_class=DischargeSummaryReportAuthorizer,
    description="Discharge summary generated for an encounter",
)
ReportTypeRegistry.register(
    key="patient_summary",
    display_name="Patient Summary",
    associating_model=Patient,
    authorizer_class=PatientReportAuthorizer,
    description="Patient summary generated for a patient",
)

ReportTypeRegistry.register(
    key="account_report",
    display_name="Account Report",
    associating_model=Account,
    authorizer_class=AccountReportAuthorizer,
    description="Account report generated for an account",
)

ReportTypeRegistry.register(
    key="encounter_report",
    display_name="Encounter Report",
    associating_model=Encounter,
    authorizer_class=EncounterReportAuthorizer,
    description="Encounter report generated for an encounter",
)
