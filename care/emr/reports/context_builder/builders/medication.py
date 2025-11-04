from care.emr.models import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import contex_builder_registry
from care.emr.reports.context_builder.utils import format_datetime

STATUS_DISPLAY = {
    "active": "Active",
    "on_hold": "On Hold",
    "cancelled": "Cancelled",
    "completed": "Completed",
    "entered_in_error": "Entered in Error",
    "stopped": "Stopped",
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
    "option": "Option",
}

PRIORITY_DISPLAY = {
    "routine": "Routine",
    "urgent": "Urgent",
    "asap": "ASAP",
    "stat": "STAT",
}

STATUS_REASON_DISPLAY = {
    "altchoice": "Alternative Choice",
    "clarif": "Clarification Needed",
    "drughigh": "Drug Level Too High",
    "hospadm": "Hospital Admission",
    "labint": "Lab Interference Issues",
    "non_avail": "Patient Not Available",
    "preg": "Pregnancy",
    "salg": "Allergy",
    "sddi": "Drug Interacts with Another Drug",
    "sdupther": "Duplicate Therapy",
    "sintol": "Suspected Intolerance",
    "surg": "Patient Scheduled for Surgery",
    "washout": "Washout Period",
}


class MedicationContextBuilder(QuerysetContextBuilder):
    model = MedicationRequest

    base_filters = {}
    allowed_filters = ["status", "intent", "priority", "authored_on"]

    fields = [
        Field(
            key="medication_name",
            display="Medication Name",
            mapping=lambda m: (
                m.medication.get("display", "")
                if isinstance(m.medication, dict)
                else str(m.medication)
                if m.medication
                else ""
            ),
            preview_value="Metformin 500mg",
            description="Name and strength of medication",
        ),
        Field(
            key="dosage",
            display="Dosage Instructions",
            mapping=lambda m: (
                m.dosage_instruction[0].get("text", "")
                if m.dosage_instruction and len(m.dosage_instruction) > 0
                else ""
            ),
            preview_value="1 tablet twice daily after meals",
            description="How to take the medication",
        ),
        Field(
            key="route",
            display="Route of Administration",
            mapping=lambda m: (
                m.dosage_instruction[0].get("route", {}).get("display", "")
                if m.dosage_instruction and len(m.dosage_instruction) > 0
                else ""
            ),
            preview_value="Oral",
            description="How the medication is administered",
        ),
        Field(
            key="frequency",
            display="Frequency",
            mapping=lambda m: (
                m.dosage_instruction[0]
                .get("timing", {})
                .get("code", {})
                .get("display", "")
                if m.dosage_instruction and len(m.dosage_instruction) > 0
                else ""
            ),
            preview_value="Twice daily",
            description="How often to take",
        ),
        Field(
            key="status",
            display="Status",
            mapping=lambda m: STATUS_DISPLAY.get(
                m.status, m.status.replace("_", " ").title() if m.status else ""
            ),
            preview_value="Active",
            description="Current status of the prescription",
        ),
        Field(
            key="intent",
            display="Intent",
            mapping=lambda m: INTENT_DISPLAY.get(
                m.intent, m.intent.title() if m.intent else ""
            ),
            preview_value="Order",
            description="Intent of the medication request",
        ),
        Field(
            key="priority",
            display="Priority",
            mapping=lambda m: PRIORITY_DISPLAY.get(
                m.priority, m.priority.title() if m.priority else ""
            ),
            preview_value="Routine",
            description="Priority of the medication",
        ),
        Field(
            key="prescribed_date",
            display="Prescribed Date",
            mapping=lambda m: format_datetime(m.authored_on) if m.authored_on else "",
            preview_value="10/01/2024 10:30 AM",
            description="Date when medication was prescribed",
        ),
        Field(
            key="note",
            display="Notes",
            mapping="note",
            preview_value="Take with food",
            description="Additional instructions",
        ),
        Field(
            key="status_reason",
            display="Status Reason",
            mapping=lambda m: STATUS_REASON_DISPLAY.get(
                m.status_reason,
                m.status_reason.replace("_", " ").title() if m.status_reason else "",
            ),
            preview_value="",
            description="Reason for the medication status",
        ),
        Field(
            key="logged_by",
            display="Logged By",
            mapping=lambda m: m.created_by.get_display_name() if m.created_by else "",
            preview_value="Dr. Kavita Desai",
            description="Person who prescribed this medication",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        if not encounter_id:
            raise ValueError("encounter_id is required in context to build medications")

        try:
            encounter = Encounter.objects.get(external_id=encounter_id)
        except Encounter.DoesNotExist as e:
            msg = f"Encounter with id {encounter_id} not found"
            raise ValueError(msg) from e

        queryset = cls.model.objects.filter(encounter=encounter)

        if cls.base_filters:
            queryset = queryset.filter(**cls.base_filters)

        return queryset

    @classmethod
    def get_display_name(cls):
        return "Medications"

    @classmethod
    def get_description(cls):
        return "Prescribed medications"


contex_builder_registry.register("medications", MedicationContextBuilder)
