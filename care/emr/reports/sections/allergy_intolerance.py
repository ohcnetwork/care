from care.emr.models import AllergyIntolerance
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection

CLINICAL_STATUS_DISPLAY = {
    "active": "Active",
    "inactive": "Inactive",
    "resolved": "Resolved",
}

VERIFICATION_STATUS_DISPLAY = {
    "unconfirmed": "Unconfirmed",
    "presumed": "Presumed",
    "confirmed": "Confirmed",
    "refuted": "Refuted",
    "entered_in_error": "Entered in Error",
}

CATEGORY_DISPLAY = {
    "food": "Food",
    "medication": "Medication",
    "environment": "Environment",
    "biologic": "Biologic",
}

CRITICALITY_DISPLAY = {
    "low": "Low",
    "high": "High",
    "unable_to_assess": "Unable to Assess",
}

ALLERGY_INTOLERANCE_TYPE_DISPLAY = {
    "allergy": "Allergy",
    "intolerance": "Intolerance",
}


class AllergyIntoleranceSection(BaseSection):
    __model__ = AllergyIntolerance

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.register_field("allergen", lambda o: o.code.get("display"))
        self.register_field("onset", lambda o: o.onset.get("onset_datetime"))
        self.register_field(
            "clinical_status",
            lambda o: CLINICAL_STATUS_DISPLAY.get(o.clinical_status, o.clinical_status),
        )
        self.register_field(
            "criticality",
            lambda o: CRITICALITY_DISPLAY.get(o.criticality, o.criticality),
        )
        self.register_field("note", lambda o: o.note)
        self.register_field("logged_by", lambda o: o.created_by.full_name)
        self.register_field("last_occurrence", lambda o: o.last_occurrence)
        self.register_field(
            "verification_status",
            lambda o: VERIFICATION_STATUS_DISPLAY.get(
                o.verification_status, o.verification_status
            ),
        )
        self.register_field(
            "type",
            lambda o: ALLERGY_INTOLERANCE_TYPE_DISPLAY.get(
                o.allergy_intolerance_type, o.allergy_intolerance_type
            ),
        )

    def fetch_data(self):
        return AllergyIntolerance.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("allergy_intolerance", AllergyIntoleranceSection)
