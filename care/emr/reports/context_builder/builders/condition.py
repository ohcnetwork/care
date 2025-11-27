from care.emr.models import Encounter
from care.emr.models.condition import Condition
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import context_builder_registry
from care.emr.reports.context_builder.utils import format_date

CLINICAL_STATUS_DISPLAY = {
    "active": "Active",
    "recurrence": "Recurrence",
    "relapse": "Relapse",
    "inactive": "Inactive",
    "remission": "Remission",
    "resolved": "Resolved",
    "unknown": "Unknown",
}

VERIFICATION_STATUS_DISPLAY = {
    "unconfirmed": "Unconfirmed",
    "provisional": "Provisional",
    "differential": "Differential",
    "confirmed": "Confirmed",
    "refuted": "Refuted",
    "entered_in_error": "Entered in Error",
}

SEVERITY_DISPLAY = {
    "mild": "Mild",
    "moderate": "Moderate",
    "severe": "Severe",
}


class DiagnosisContextBuilder(QuerysetContextBuilder):
    model = Condition
    depends_on = ["encounter_id"]

    base_filters = {"category": "encounter_diagnosis"}
    allowed_filters = [
        Condition.clinical_status,
        Condition.verification_status,
        Condition.severity,
    ]

    fields = [
        Field(
            key="diagnosis_name",
            display="Diagnosis Name",
            mapping=lambda c: c.code.get("display", "")
            if isinstance(c.code, dict)
            else "",
            preview_value="Type 2 Diabetes Mellitus",
            description="Name of the diagnosis",
        ),
        Field(
            key="clinical_status",
            display="Clinical Status",
            mapping=lambda c: CLINICAL_STATUS_DISPLAY.get(
                c.clinical_status, c.clinical_status
            )
            if c.clinical_status
            else "",
            preview_value="Active",
            description="Clinical status of the condition",
        ),
        Field(
            key="verification_status",
            display="Verification Status",
            mapping=lambda c: VERIFICATION_STATUS_DISPLAY.get(
                c.verification_status, c.verification_status
            )
            if c.verification_status
            else "",
            preview_value="Confirmed",
            description="Status of diagnosis verification",
        ),
        Field(
            key="severity",
            display="Severity",
            mapping=lambda c: SEVERITY_DISPLAY.get(
                c.severity, c.severity.title() if c.severity else ""
            ),
            preview_value="Moderate",
            description="Severity of the condition",
        ),
        Field(
            key="onset_date",
            display="Onset Date",
            mapping=lambda c: (
                format_date(c.onset.get("onset_datetime"))
                if isinstance(c.onset, dict) and c.onset.get("onset_datetime")
                else ""
            ),
            preview_value="08/01/2024",
            description="When the condition started",
        ),
        Field(
            key="note",
            display="Notes",
            mapping="note",
            preview_value="Patient managing condition with medication",
            description="Additional notes about the diagnosis",
        ),
        Field(
            key="logged_by",
            display="Logged By",
            mapping=lambda c: c.created_by.full_name if c.created_by else "",
            preview_value="Dr. Arjun Sharma",
            description="Person who logged this diagnosis",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        encounter = Encounter.objects.get(external_id=encounter_id)

        queryset = cls.model.objects.filter(encounter=encounter)

        if cls.base_filters:
            queryset = queryset.filter(**cls.base_filters)

        return queryset

    @classmethod
    def get_display_name(cls):
        return "Diagnoses"

    @classmethod
    def get_description(cls):
        return "Patient diagnosis list"


class SymptomContextBuilder(QuerysetContextBuilder):
    model = Condition
    depends_on = ["encounter_id"]

    base_filters = {"category": "problem_list_item"}
    allowed_filters = [
        Condition.clinical_status,
        Condition.verification_status,
        Condition.severity,
    ]

    fields = [
        Field(
            key="symptom_name",
            display="Symptom",
            mapping=lambda c: c.code.get("display", "")
            if isinstance(c.code, dict)
            else "",
            preview_value="Fever",
            description="Name of the symptom",
        ),
        Field(
            key="clinical_status",
            display="Status",
            mapping=lambda c: CLINICAL_STATUS_DISPLAY.get(
                c.clinical_status, c.clinical_status
            )
            if c.clinical_status
            else "",
            preview_value="Active",
            description="Current status of the symptom",
        ),
        Field(
            key="severity",
            display="Severity",
            mapping=lambda c: SEVERITY_DISPLAY.get(
                c.severity, c.severity.title() if c.severity else ""
            ),
            preview_value="Moderate",
            description="Severity of the symptom",
        ),
        Field(
            key="onset_date",
            display="Onset Date",
            mapping=lambda c: (
                format_date(c.onset.get("onset_datetime"))
                if isinstance(c.onset, dict) and c.onset.get("onset_datetime")
                else ""
            ),
            preview_value="10/01/2024",
            description="When the symptom started",
        ),
        Field(
            key="note",
            display="Notes",
            mapping="note",
            preview_value="Patient reports high grade fever",
            description="Additional notes about the symptom",
        ),
        Field(
            key="logged_by",
            display="Logged By",
            mapping=lambda c: c.created_by.full_name if c.created_by else "",
            preview_value="Dr. Priya Patel",
            description="Person who logged this symptom",
        ),
        Field(
            key="verification_status",
            display="Verification Status",
            mapping=lambda c: VERIFICATION_STATUS_DISPLAY.get(
                c.verification_status, c.verification_status
            )
            if c.verification_status
            else "",
            preview_value="Confirmed",
            description="Status of symptom verification",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        encounter = Encounter.objects.get(external_id=encounter_id)

        queryset = cls.model.objects.filter(encounter=encounter)

        if cls.base_filters:
            queryset = queryset.filter(**cls.base_filters)

        return queryset

    @classmethod
    def get_display_name(cls):
        return "Symptoms"

    @classmethod
    def get_description(cls):
        return "Patient reported symptoms"


context_builder_registry.register("diagnoses", DiagnosisContextBuilder)
context_builder_registry.register("symptoms", SymptomContextBuilder)
