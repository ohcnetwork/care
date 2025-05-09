from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection

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
    "non_binary": "Non-binary",
    "transgender": "Transgender",
}


class PatientInfoSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.register_field("name", lambda o: o.name)
        self.register_field("gender", lambda o: GENDER_DISPLAY.get(o.gender, o.gender))
        self.register_field("phone_number", lambda o: o.phone_number)
        self.register_field(
            "emergency_phone_number", lambda o: o.emergency_phone_number
        )
        self.register_field("address", lambda o: o.address)
        self.register_field("permanent_address", lambda o: o.permanent_address)
        self.register_field("pincode", lambda o: o.pincode)
        self.register_field("date_of_birth", lambda o: o.date_of_birth)
        self.register_field("year_of_birth", lambda o: o.year_of_birth)
        self.register_field("deceased_datetime", lambda o: o.deceased_datetime)
        self.register_field("marital_status", lambda o: o.marital_status)
        self.register_field(
            "blood_group",
            lambda o: BLOOD_GROUP_DISPLAY.get(o.blood_group, o.blood_group),
        )
        self.register_field("age", lambda o: o.get_age())

    def fetch_data(self):
        return [self.context["encounter"].patient]


SectionRegistry.register("patient_info", PatientInfoSection)
