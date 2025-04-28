from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class PatientInfoSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

    def fetch_data(self):
        return [self.context["encounter"].patient]


SectionRegistry.register("patient_info", PatientInfoSection)
