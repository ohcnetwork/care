from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.reports.report_type_registry import ReportTypeRegistry

ReportTypeRegistry.register(
    key="discharge_summary",
    display_name="Discharge Summary",
    associating_model=Encounter,
    description="Discharge summary generated at the end of an encounter",
)

ReportTypeRegistry.register(
    key="patient_card",
    display_name="Patient Card",
    associating_model=Patient,
    description="Patient identification card with basic information",
)

ReportTypeRegistry.register(
    key="prescription",
    display_name="Prescription",
    associating_model=Encounter,
    description="Medication prescription for an encounter",
)

ReportTypeRegistry.register(
    key="lab_report",
    display_name="Lab Report",
    associating_model=Encounter,
    description="Laboratory test results for an encounter",
)

ReportTypeRegistry.register(
    key="consent_form",
    display_name="Consent Form",
    associating_model=Encounter,
    description="Medical consent form for procedures",
)

ReportTypeRegistry.register(
    key="medical_certificate",
    display_name="Medical Certificate",
    associating_model=Encounter,
    description="Medical fitness or sick leave certificate",
)

ReportTypeRegistry.register(
    key="billing_statement",
    display_name="Billing Statement",
    associating_model=Patient,
    description="Billing and payment statement for a patient",
)
