from care.emr.models import AllergyIntolerance
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class AllergyIntoleranceSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.field_extractors.update(
            {
                "allergen": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return AllergyIntolerance.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("allergy_intolerance", AllergyIntoleranceSection)
