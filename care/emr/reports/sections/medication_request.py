from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection

STATUS_REASON_DISPLAY = {
    "altchoice": "Try another treatment first",
    "clarif": "Prescription requires clarification",
    "drughigh": "Drug level too high",
    "hospadm": "Admission to hospital",
    "labint": "Lab interference issues",
    "non_avail": "Patient not available",
    "preg": "Parent is pregnant/breast feeding",
    "salg": "Allergy",
    "sddi": "Drug interacts with another drug",
    "sdupther": "Duplicate therapy",
    "sintol": "Suspected intolerance",
    "surg": "Patient scheduled for surgery",
    "washout": "Waiting for old drug to wash out",
}

STATUS_DISPLAY = {
    "active": "Active",
    "on_hold": "On Hold",
    "ended": "Ended",
    "stopped": "Stopped",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "entered_in_error": "Entered in Error",
    "draft": "Draft",
    "unknown": "Unknown",
}

INTENT_DISPLAY = {
    "proposal": "Proposal",
    "plan": "Plan",
    "order": "Order",
    "original_order": "Original Order",
    "reflex_order": "Reflex Order",
    "filler_order": "Filler Order",
    "instance_order": "Instance Order",
}

PRIORITY_DISPLAY = {
    "routine": "Routine",
    "urgent": "Urgent",
    "asap": "As Soon As Possible",
    "stat": "Immediately (Stat)",
}

CATEGORY_DISPLAY = {
    "inpatient": "Inpatient",
    "outpatient": "Outpatient",
    "community": "Community",
    "discharge": "Discharge",
}


def _med_dosage_instructions(o: MedicationRequest):
    try:
        dosage = o.dosage_instruction[0]
        # Prefer text if available
        if dosage.get("text"):
            return dosage["text"]

        dose_val = dosage.get("dose_and_rate", {}).get("dose_quantity", {}).get("value")
        dose_unit = (
            dosage.get("dose_and_rate", {})
            .get("dose_quantity", {})
            .get("unit", {})
            .get("display", "")
        )

        timing = dosage.get("timing", {})
        timing_display = timing.get("code", {}).get("display")
        repeat = timing.get("repeat", {})
        freq = repeat.get("frequency")
        period = repeat.get("period")
        period_unit = repeat.get("period_unit")
        duration = repeat.get("bounds_duration", {}).get("value")
        duration_unit = repeat.get("bounds_duration", {}).get("unit")

        # Build readable string
        parts = []

        if dose_val and dose_unit:
            parts.append(f"Take {dose_val} {dose_unit}")

        if timing_display:
            parts.append(f"{timing_display}")
        elif freq and period and period_unit:
            parts.append(f"every {period} {period_unit}")

        if duration and duration_unit:
            parts.append(f"for {duration} {duration_unit}")

        return " ".join(parts) if parts else BaseSection.DEFAULT_EMPTY

    except Exception:
        return BaseSection.DEFAULT_EMPTY


class MedicationRequestSection(BaseSection):
    __model__ = MedicationRequest

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

        self.register_field("medication", lambda m: m.medication.get("display"))
        self.register_field("instructions", lambda o: _med_dosage_instructions(o))
        self.register_field("date", lambda m: m.authored_on or m.created_date)
        self.register_field("intent", lambda o: INTENT_DISPLAY.get(o.intent, o.intent))
        self.register_field(
            "priority", lambda o: PRIORITY_DISPLAY.get(o.priority, o.priority)
        )
        self.register_field(
            "status_reason",
            lambda o: STATUS_REASON_DISPLAY.get(o.status_reason, o.status_reason),
        )
        self.register_field("status", lambda o: STATUS_DISPLAY.get(o.status, o.status))
        self.register_field("logged_by", lambda o: o.created_by.full_name)

    def fetch_data(self):
        return MedicationRequest.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("medication_request", MedicationRequestSection)
