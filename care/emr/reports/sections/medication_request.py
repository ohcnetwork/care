from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


def _med_dosage(o: MedicationRequest):
    try:
        return o.dosage_instruction[0]["text"] or BaseSection.DEFAULT_EMPTY
    except Exception:
        return BaseSection.DEFAULT_EMPTY


class MedicationRequestSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.field_extractors.update(
            {
                "medication": lambda m: m.medication.get("display", self.DEFAULT_EMPTY),
                "value": _med_dosage,
                "date": lambda m: m.authored_on or m.created_date or self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return MedicationRequest.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("medication_request", MedicationRequestSection)
