from care.emr.models import Encounter
from care.emr.models.condition import Condition
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import contex_builder_registry
from care.emr.reports.context_builder.utils import format_date, format_datetime

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

    base_filters = {"category": "diagnosis"}

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
            key="diagnosis_code",
            display="Diagnosis Code",
            mapping=lambda c: c.code.get("code", "")
            if isinstance(c.code, dict)
            else "",
            preview_value="5A11",
            description="Medical code for the diagnosis",
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
            key="recorded_date",
            display="Recorded Date",
            mapping=lambda c: format_date(c.recorded_date) if c.recorded_date else "",
            preview_value="10/01/2024",
            description="Date when diagnosis was recorded",
        ),
        Field(
            key="onset_date",
            display="Onset Date",
            mapping=lambda c: (
                format_datetime(c.onset.get("dateTime"))
                if isinstance(c.onset, dict) and c.onset.get("dateTime")
                else ""
            ),
            preview_value="08/01/2024",
            description="When the condition started",
        ),
        Field(
            key="body_site",
            display="Body Site",
            mapping=lambda c: c.body_site.get("display", "")
            if isinstance(c.body_site, dict)
            else "",
            preview_value="Pancreas",
            description="Anatomical location",
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
            mapping=lambda c: c.created_by.get_display_name() if c.created_by else "",
            preview_value="Dr. Arjun Sharma",
            description="Person who logged this diagnosis",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        """Get diagnosis queryset filtered by encounter"""
        encounter_id = ctx.get("encounter_id")
        if not encounter_id:
            raise ValueError("encounter_id is required in context to build diagnoses")

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
        return "Diagnoses"

    @classmethod
    def get_description(cls):
        return "Patient diagnosis list"


class SymptomContextBuilder(QuerysetContextBuilder):
    model = Condition

    base_filters = {"category": "symptom"}

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
                format_datetime(c.onset.get("dateTime"))
                if isinstance(c.onset, dict) and c.onset.get("dateTime")
                else ""
            ),
            preview_value="10/01/2024",
            description="When the symptom started",
        ),
        Field(
            key="abatement_date",
            display="Resolution Date",
            mapping=lambda c: (
                format_datetime(c.abatement.get("dateTime"))
                if isinstance(c.abatement, dict) and c.abatement.get("dateTime")
                else ""
            ),
            preview_value="15/01/2024",
            description="When the symptom resolved",
        ),
        Field(
            key="body_site",
            display="Body Site",
            mapping=lambda c: c.body_site.get("display", "")
            if isinstance(c.body_site, dict)
            else "",
            preview_value="Throat",
            description="Anatomical location of symptom",
        ),
        Field(
            key="duration",
            display="Duration",
            mapping=lambda c: (
                f"{(c.abatement.get('dateTime') - c.onset.get('dateTime')).days} days"
                if isinstance(c.onset, dict)
                and isinstance(c.abatement, dict)
                and c.onset.get("dateTime")
                and c.abatement.get("dateTime")
                else "Ongoing"
            ),
            preview_value="5 days",
            description="Duration of the symptom",
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
            mapping=lambda c: c.created_by.get_display_name() if c.created_by else "",
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
        if not encounter_id:
            raise ValueError("encounter_id is required in context to build symptoms")

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
        return "Symptoms"

    @classmethod
    def get_description(cls):
        return "Patient reported symptoms"


contex_builder_registry.register("diagnoses", DiagnosisContextBuilder)
contex_builder_registry.register("symptoms", SymptomContextBuilder)
