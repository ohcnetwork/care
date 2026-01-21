from care.emr.models.patient import Patient, PatientIdentifierConfig
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)

GENDER_CHOICES = {
    "male": "Male",
    "female": "Female",
    "non_binary": "Non binary",
    "transgender": "Transgender",
}

IDENTIFIER_USE_OPTIONS = {
    "official": "Official",
    "usual": "Usual",
    "temp": "Temporary",
    "secondary": "Secondary",
    "old": "Old",
}


class IdentifierConfigContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return PatientIdentifierConfig.objects.filter(
            external_id=self.parent_context.get("config"), status="active"
        ).first()

    display = Field(
        display="Display",
        preview_value="Patient ID",
        mapping=lambda ic: ic.config.get("display")
        if ic and ic.config and ic.config.get("display")
        else None,
        description="Display of the identifier configuration",
    )

    use = Field(
        display="Use",
        preview_value="Official",
        mapping=lambda ic: IDENTIFIER_USE_OPTIONS.get(
            ic.config.get("use"), ic.config.get("use").title()
        )
        if ic and ic.config and ic.config.get("use")
        else None,
        description="Use of the identifier configuration",
    )

    auto_maintained = Field(
        display="Auto Maintained",
        preview_value="False",
        mapping=lambda ic: ic.config.get("auto_maintained", False)
        if ic and ic.config
        else None,
        description="Whether the identifier is auto maintained",
    )


class IdentifiersContextBuilder(QuerysetContextBuilder):
    config = Field(
        display="Config",
        preview_value="Config",
        target_context=IdentifierConfigContextBuilder,
        description="Patient Identifier Configuration",
    )

    value = Field(
        display="Identifier Value",
        preview_value="12342",
        mapping=lambda i: i.get("value") if i and i.get("value") else "",
        description="Value of the patient identifier",
    )


class PatientInstanceIdentifiersContextBuilder(IdentifiersContextBuilder):
    def get_context(self):
        return self.parent_context.instance_identifiers


class PatientFacilityIdentifiersContextBuilder(IdentifiersContextBuilder):
    def get_context(self):
        return self.parent_context.facility_identifiers


class BasePatientContextBuilder(SingleObjectContextBuilder):
    name = Field(
        display="Patient Name",
        preview_value="John Doe",
        description="Full name of the patient",
    )

    gender = Field(
        display="Patient Gender",
        preview_value="Male",
        mapping=lambda p: GENDER_CHOICES.get(p.gender, p.gender.title())
        if p.gender
        else "",
        description="Gender of the patient",
    )
    age = Field(
        display="Patient Age",
        mapping=lambda p: p.get_age(),
        preview_value="45 Y",
        description="Age of the patient",
    )

    blood_group = Field(
        display="Patient Blood Group",
        preview_value="A Positive",
        mapping=lambda p: p.blood_group.replace("_", " ").title()
        if p.blood_group
        else "",
        description="Blood group of the patient",
    )

    address = Field(
        display="Patient Address",
        preview_value="123 Main St, Springfield",
        description="Address of the patient",
    )
    phone_number = Field(
        display="Patient Phone Number",
        preview_value="+91 9876543210",
        description="Phone number of the patient",
    )

    date_of_birth = Field(
        display="Patient Date of Birth",
        mapping="date_of_birth",
        preview_value="1978-05-15",
        description="Date of birth of the patient",
    )
    deceased_datetime = Field(
        display="Patient Deceased Datetime",
        mapping="deceased_datetime",
        preview_value="",
        description="Datetime when the patient was declared deceased",
    )
    instance_identifiers = Field(
        display="Patient Instance Identifiers",
        target_context=PatientInstanceIdentifiersContextBuilder,
        preview_value="",
        description="Instance identifiers associated with the patient",
    )
    facility_identifiers = Field(
        display="Patient Facility Identifiers",
        target_context=PatientFacilityIdentifiersContextBuilder,
        preview_value="",
        description="Facility-specific identifiers associated with the patient",
    )


class PatientMinimumContextBuilder(BasePatientContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)


class PatientContextBuilderBase(BasePatientContextBuilder):
    standalone_context = True
    __slug__ = "patient_base"
    __associating_model__ = Patient
    __display_name__ = "Patient Report"
    __description__ = "Report context for patient-based reports"
    context_key = "patient"


DataPointRegistry.register(PatientContextBuilderBase)
