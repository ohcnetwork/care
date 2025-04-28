from care.emr.models import Condition
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection
from care.emr.resources.condition.spec import CategoryChoices


class SymptomSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.field_extractors.update(
            {
                "symptom": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.problem_list_item,
        )


SectionRegistry.register("symptoms", SymptomSection)
