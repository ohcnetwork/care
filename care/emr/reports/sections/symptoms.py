from datetime import datetime

from care.emr.models import Condition
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection
from care.emr.resources.condition.spec import CategoryChoices

CLINICAL_STATUS_DISPLAY = {
    "active": "Active",
    "recurrence": "Recurrence",
    "relapse": "Relapse",
    "inactive": "Inactive",
    "remission": "Remission",
    "resolved": "Resolved",
    "unknown": "Unknown",
}

VERIFICATION_STATUS_DISPLAY = {
    "unconfirmed": "Unconfirmed",
    "provisional": "Provisional",
    "differential": "Differential",
    "confirmed": "Confirmed",
    "refuted": "Refuted",
    "entered_in_error": "Entered in Error",
}

SEVERITY_DISPLAY = {
    "mild": "Mild",
    "moderate": "Moderate",
    "severe": "Severe",
}


class SymptomSection(BaseSection):
    __model__ = Condition

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.register_field("symptom", lambda o: o.code.get("display"))
        self.register_field(
            "onset",
            lambda o: (datetime.fromisoformat(o.onset.get("onset_datetime")).date()),
        )
        self.register_field(
            "status",
            lambda o: CLINICAL_STATUS_DISPLAY.get(o.clinical_status, o.clinical_status),
        )
        self.register_field(
            "verification",
            lambda o: VERIFICATION_STATUS_DISPLAY.get(
                o.verification_status, o.verification_status
            ),
        )
        self.register_field(
            "severity", lambda o: SEVERITY_DISPLAY.get(o.severity, o.severity)
        )
        self.register_field("note", lambda o: o.note)
        self.register_field("logged_by", lambda o: o.created_by.full_name)

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.problem_list_item,
        )


SectionRegistry.register("symptoms", SymptomSection)
