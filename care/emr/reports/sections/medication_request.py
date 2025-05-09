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

        self.register_field("medication", lambda m: m.medication.get("display"))
        self.register_field("value", lambda o: _med_dosage)
        self.register_field("date", lambda m: m.authored_on or m.created_date)
        self.register_field("requested_by", lambda o: o.requester.full_name)
        self.register_field("intent", lambda o: o.intent)
        self.register_field("priority", lambda o: o.priority)
        self.register_field("status_reason", lambda o: o.status_reason)
        self.register_field("status", lambda o: o.status)
        self.register_field("logged_by", lambda o: o.created_by.full_name)

    def fetch_data(self):
        return MedicationRequest.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("medication_request", MedicationRequestSection)
