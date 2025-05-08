from datetime import datetime

from care.emr.models import Condition
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection
from care.emr.resources.condition.spec import CategoryChoices


class DiagnosisSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.field_extractors.update(
            {
                "diagnosis": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: (
                    datetime.fromisoformat(o.onset.get("onset_datetime")).date()
                    if o.onset and o.onset.get("onset_datetime")
                    else self.DEFAULT_EMPTY
                ),
            }
        )

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.encounter_diagnosis,
        )


SectionRegistry.register("diagnosis", DiagnosisSection)
