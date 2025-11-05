from care.emr.models.patient import Patient
from care.emr.reports.context_builder.base import Field, SingleObjectContextBuilder
from care.emr.reports.context_builder.registry import contex_builder_registry
from care.emr.reports.context_builder.utils import format_date, format_phone_number

BLOOD_GROUP_DISPLAY = {
    "A_positive": "A+",
    "A_negative": "A-",
    "B_positive": "B+",
    "B_negative": "B-",
    "AB_positive": "AB+",
    "AB_negative": "AB-",
    "O_positive": "O+",
    "O_negative": "O-",
    "unknown": "Unknown",
}

GENDER_DISPLAY = {
    "male": "Male",
    "female": "Female",
    "non_binary": "Non-Binary",
    "transgender": "Transgender",
}


class PatientContextBuilder(SingleObjectContextBuilder):
    model = Patient
    depends_on = ["patient_id"]

    fields = [
        Field(
            key="name",
            display="Patient Name",
            mapping="name",
            preview_value="Ramesh Kumar",
            description="Full legal name of the patient",
        ),
        Field(
            key="age",
            display="Age",
            mapping=lambda p: p.get_age(),
            preview_value="45 years",
            description="Current age of the patient",
        ),
        Field(
            key="gender",
            display="Gender",
            mapping=lambda p: GENDER_DISPLAY.get(p.gender, p.gender)
            if p.gender
            else "",
            preview_value="Male",
            description="Gender of the patient",
        ),
        Field(
            key="blood_group",
            display="Blood Group",
            mapping=lambda p: BLOOD_GROUP_DISPLAY.get(p.blood_group, p.blood_group)
            if p.blood_group
            else "",
            preview_value="O+",
            description="Blood group of the patient",
        ),
        Field(
            key="date_of_birth",
            display="Date of Birth",
            mapping=lambda p: format_date(p.date_of_birth) if p.date_of_birth else "",
            preview_value="15/01/1979",
            description="Date of birth",
        ),
        Field(
            key="phone_number",
            display="Phone Number",
            mapping=lambda p: format_phone_number(p.phone_number),
            preview_value="+91 98765 43210",
            description="Primary contact number",
        ),
        Field(
            key="emergency_phone_number",
            display="Emergency Contact",
            mapping=lambda p: format_phone_number(p.emergency_phone_number)
            if p.emergency_phone_number
            else "",
            preview_value="+91 98765 43211",
            description="Emergency contact number",
        ),
        Field(
            key="address",
            display="Address",
            mapping="address",
            preview_value="123, MG Road, Koramangala, Bangalore, Karnataka - 560034",
            description="Current residential address",
        ),
        Field(
            key="permanent_address",
            display="Permanent Address",
            mapping="permanent_address",
            preview_value="456, Church Street, Indiranagar, Bangalore, Karnataka - 560038",
            description="Permanent address",
        ),
        Field(
            key="pincode",
            display="Pincode",
            mapping=lambda p: str(p.pincode) if p.pincode else "",
            preview_value="560034",
            description="Pincode of current address",
        ),
        Field(
            key="marital_status",
            display="Marital Status",
            mapping=lambda p: p.marital_status.replace("_", " ").title()
            if p.marital_status
            else "",
            preview_value="Married",
            description="Marital status of the patient",
        ),
        Field(
            key="year_of_birth",
            display="Year of Birth",
            mapping=lambda p: str(p.year_of_birth) if p.year_of_birth else "",
            preview_value="1979",
            description="Year of birth",
        ),
        Field(
            key="deceased_datetime",
            display="Deceased Date/Time",
            mapping=lambda p: str(p.deceased_datetime) if p.deceased_datetime else "",
            preview_value="",
            description="Date and time of death (if applicable)",
        ),
    ]

    @classmethod
    def get_object(cls, ctx: dict):
        patient_id = ctx.get("patient_id")
        return Patient.objects.get(external_id=patient_id)

    @classmethod
    def get_display_name(cls):
        return "Patient Information"

    @classmethod
    def get_description(cls):
        return "Basic patient demographics and contact information"


contex_builder_registry.register("patient", PatientContextBuilder)
