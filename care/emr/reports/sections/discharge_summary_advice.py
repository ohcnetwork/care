from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class DischargeSummaryAdviceSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

    def fetch_data(self):
        return [self.context["encounter"].discharge_summary_advice or ""]


SectionRegistry.register("discharge_summary_advice", DischargeSummaryAdviceSection)
