from care.emr.models import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import context_builder_registry
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


class MedicationContextBuilder(QuerysetContextBuilder):
    model = MedicationRequest
    depends_on = ["encounter_id"]

    base_filters = {}
    allowed_filters = [
        MedicationRequest.status,
        MedicationRequest.intent,
        MedicationRequest.priority,
        MedicationRequest.authored_on,
    ]

    fields = [
        Field(
            key="medication_name",
            display="Medication Name",
            mapping=lambda m: (
                m.requested_product.name
                if m.requested_product
                else (
                    m.medication.get("display", "")
                    if isinstance(m.medication, dict)
                    else str(m.medication)
                    if m.medication
                    else ""
                )
            ),
            preview_value="Metformin 500mg",
            description="Name and strength of medication",
        ),
        Field(
            key="dosage_instructions",
            display="Dosage Instructions",
            field_type="list[DosageInstruction]",
            mapping=lambda m: MedicationContextBuilder._format_dosage_instructions(m),
            preview_value=[
                {
                    "dose": "1 tablet",
                    "route": "Oral",
                    "frequency": "Twice daily",
                    "duration": "7 days",
                    "site": "",
                    "method": "",
                    "as_needed": False,
                    "additional_instructions": ["Take with food"],
                }
            ],
            description="List of all dosage instructions for this medication",
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
            key="logged_by",
            display="Logged By",
            mapping=lambda m: m.created_by.full_name if m.created_by else "",
            preview_value="Dr. Kavita Desai",
            description="Person who prescribed this medication",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        encounter = Encounter.objects.get(external_id=encounter_id)

        queryset = cls.model.objects.filter(encounter=encounter).select_related(
            "requested_product", "created_by"
        )

        if cls.base_filters:
            queryset = queryset.filter(**cls.base_filters)

        return queryset

    @classmethod
    def get_display_name(cls):
        return "Medications"

    @classmethod
    def get_description(cls):
        return "Prescribed medications"

    @staticmethod
    def _format_dosage_instructions(medication):
        if not medication.dosage_instruction:
            return []

        instructions = []
        for dosage in medication.dosage_instruction:
            dose_and_rate = dosage.get("dose_and_rate", {})
            dose_quantity = dose_and_rate.get("dose_quantity", {})
            timing = dosage.get("timing", {})
            repeat = timing.get("repeat", {})
            bounds_duration = repeat.get("bounds_duration", {})

            dose_text = ""
            if dose_quantity.get("value"):
                unit_display = (
                    dose_quantity.get("unit", {}).get("display", "")
                    if isinstance(dose_quantity.get("unit"), dict)
                    else ""
                )
                dose_text = f"{dose_quantity['value']} {unit_display}".strip()

            duration_text = ""
            if bounds_duration.get("value"):
                duration_unit = (
                    bounds_duration.get("unit", {}).get("display", "days")
                    if isinstance(bounds_duration.get("unit"), dict)
                    else bounds_duration.get("unit", "days")
                )
                duration_text = f"{bounds_duration['value']} {duration_unit}"

            additional_instructions = [
                instr.get("display", "")
                for instr in dosage.get("additional_instruction", [])
                if isinstance(instr, dict)
            ]

            instructions.append(
                {
                    "dose": dose_text,
                    "route": dosage.get("route", {}).get("display", ""),
                    "frequency": timing.get("code", {}).get("display", ""),
                    "duration": duration_text,
                    "site": dosage.get("site", {}).get("display", ""),
                    "method": dosage.get("method", {}).get("display", ""),
                    "as_needed": dosage.get("as_needed_boolean", False),
                    "additional_instructions": additional_instructions,
                }
            )

        return instructions


context_builder_registry.register("medications", MedicationContextBuilder)
