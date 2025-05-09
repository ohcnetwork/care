from care.emr.models import AllergyIntolerance
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class AllergyIntoleranceSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.register_field("allergen", lambda o: o.code.get("display"))
        self.register_field("onset", lambda o: o.onset.get("onset_datetime"))
        self.register_field("status", lambda o: o.clinical_status)
        self.register_field("criticality", lambda o: o.criticality)
        self.register_field("note", lambda o: o.notes)
        self.register_field("logged_by", lambda o: o.created_by.full_name)
        self.register_field("last_occurrence", lambda o: o.last_occurrence)
        self.register_field("type", lambda o: o.allergy_intolerance_type)

    def fetch_data(self):
        return AllergyIntolerance.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("allergy_intolerance", AllergyIntoleranceSection)
