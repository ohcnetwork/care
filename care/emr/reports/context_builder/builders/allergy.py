from care.emr.models import Encounter
from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import context_builder_registry
from care.emr.reports.context_builder.utils import format_date, format_datetime

CLINICAL_STATUS_DISPLAY = {
    "active": "Active",
    "inactive": "Inactive",
    "resolved": "Resolved",
}

VERIFICATION_STATUS_DISPLAY = {
    "unconfirmed": "Unconfirmed",
    "confirmed": "Confirmed",
    "refuted": "Refuted",
    "entered_in_error": "Entered in Error",
}

CATEGORY_DISPLAY = {
    "food": "Food",
    "medication": "Medication",
    "environment": "Environment",
    "biologic": "Biologic",
}

CRITICALITY_DISPLAY = {
    "low": "Low",
    "high": "High",
    "unable_to_assess": "Unable to Assess",
}

ALLERGY_INTOLERANCE_TYPE_DISPLAY = {
    "allergy": "Allergy",
    "intolerance": "Intolerance",
}


class AllergyContextBuilder(QuerysetContextBuilder):
    model = AllergyIntolerance
    depends_on = ["encounter_id"]

    allowed_filters = [
        AllergyIntolerance.clinical_status,
        AllergyIntolerance.verification_status,
        AllergyIntolerance.category,
        AllergyIntolerance.criticality,
    ]

    fields = [
        Field(
            key="allergen_name",
            display="Allergen",
            mapping=lambda a: a.code.get("display", "")
            if isinstance(a.code, dict)
            else "",
            preview_value="Penicillin",
            description="Name of the allergen",
        ),
        Field(
            key="category",
            display="Category",
            mapping=lambda a: CATEGORY_DISPLAY.get(
                a.category, a.category.replace("_", " ").title() if a.category else ""
            ),
            preview_value="Medication",
            description="Category of allergy",
        ),
        Field(
            key="criticality",
            display="Criticality",
            mapping=lambda a: CRITICALITY_DISPLAY.get(
                a.criticality,
                a.criticality.replace("_", " ").title() if a.criticality else "",
            ),
            preview_value="High",
            description="Severity level",
        ),
        Field(
            key="clinical_status",
            display="Status",
            mapping=lambda a: CLINICAL_STATUS_DISPLAY.get(
                a.clinical_status,
                a.clinical_status.replace("_", " ").title()
                if a.clinical_status
                else "",
            ),
            preview_value="Active",
            description="Current status of the allergy",
        ),
        Field(
            key="verification_status",
            display="Verification Status",
            mapping=lambda a: VERIFICATION_STATUS_DISPLAY.get(
                a.verification_status,
                a.verification_status.replace("_", " ").title()
                if a.verification_status
                else "",
            ),
            preview_value="Confirmed",
            description="Verification status",
        ),
        Field(
            key="allergy_type",
            display="Type",
            mapping=lambda a: ALLERGY_INTOLERANCE_TYPE_DISPLAY.get(
                a.allergy_intolerance_type,
                a.allergy_intolerance_type.title()
                if a.allergy_intolerance_type
                else "",
            ),
            preview_value="Allergy",
            description="Allergy or Intolerance",
        ),
        Field(
            key="recorded_date",
            display="Recorded Date",
            mapping=lambda a: format_date(a.recorded_date) if a.recorded_date else "",
            preview_value="05/01/2024",
            description="Date when allergy was recorded",
        ),
        Field(
            key="note",
            display="Notes",
            mapping="note",
            preview_value="Patient reports rash and itching",
            description="Additional information",
        ),
        Field(
            key="onset",
            display="Onset Date",
            mapping=lambda a: (
                format_datetime(a.onset.get("onset_datetime"))
                if isinstance(a.onset, dict) and a.onset.get("onset_datetime")
                else ""
            ),
            preview_value="01/01/2020 08:30 AM",
            description="When the allergy first occurred",
        ),
        Field(
            key="last_occurrence",
            display="Last Occurrence",
            mapping=lambda a: format_datetime(a.last_occurrence)
            if a.last_occurrence
            else "",
            preview_value="15/12/2023 02:15 PM",
            description="Most recent occurrence of allergic reaction",
        ),
        Field(
            key="logged_by",
            display="Logged By",
            mapping=lambda a: a.created_by.full_name if a.created_by else "",
            preview_value="Dr. Meera Iyer",
            description="Person who logged this allergy",
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
        return "Allergies"

    @classmethod
    def get_description(cls):
        return "Patient allergies and intolerances"


context_builder_registry.register("allergies", AllergyContextBuilder)
