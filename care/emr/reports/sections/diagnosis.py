from datetime import datetime

from care.emr.models import Condition
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection
from care.emr.resources.condition.spec import CategoryChoices


class DiagnosisSection(BaseSection):
    __model__ = Condition

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

        self.register_field("diagnosis", lambda o: o.code.get("display"))
        self.register_field(
            "onset",
            lambda o: (datetime.fromisoformat(o.onset.get("onset_datetime")).date()),
        )
        self.register_field("status", lambda o: o.clinical_status)
        self.register_field("verification", lambda o: o.verification_status)
        self.register_field("severity", lambda o: o.severity)
        self.register_field("note", lambda o: o.note)
        self.register_field("logged_by", lambda o: o.created_by.full_name)

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.encounter_diagnosis,
        )


SectionRegistry.register("diagnosis", DiagnosisSection)
