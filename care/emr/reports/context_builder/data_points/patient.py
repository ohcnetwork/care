from care.emr.models.patient import Patient
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.account import (
    PatientAccountContextBuilder,
)
from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)


class PatientContextBuilderBase(SingleObjectContextBuilder):
    standalone_context = True
    __slug__ = "patient_base"
    __associating_model__ = Patient
    __display_name__ = "Patient Report"
    __description__ = "Report context for patient-based reports"
    context_key = "patient"

    name = Field(
        display="Patient Name",
        preview_value="John Doe",
        description="Full name of the patient",
    )

    gender = Field(
        display="Patient Gender",
        preview_value="Male",
        description="Gender of the patient",
    )
    age = Field(
        display="Patient Age",
        mapping=lambda p: p.get_age(),
        preview_value="45 Y",
        description="Age of the patient",
    )
    accounts = Field(
        display="Patient Accounts",
        target_context=PatientAccountContextBuilder,
        preview_value="",
        description="Accounts associated with the patient",
    )


DataPointRegistry.register(PatientContextBuilderBase)
