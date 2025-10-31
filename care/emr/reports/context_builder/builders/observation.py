from care.emr.models import Encounter
from care.emr.models.observation import Observation
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import contex_builder_registry
from care.emr.reports.context_builder.utils import format_datetime

STATUS_DISPLAY = {
    "registered": "Registered",
    "preliminary": "Preliminary",
    "final": "Final",
    "amended": "Amended",
    "corrected": "Corrected",
    "cancelled": "Cancelled",
    "entered_in_error": "Entered in Error",
    "unknown": "Unknown",
}

SUBJECT_TYPE_DISPLAY = {
    "patient": "Patient",
    "encounter": "Encounter",
}


class ObservationContextBuilder(QuerysetContextBuilder):
    model = Observation

    base_filters = {}

    fields = [
        Field(
            key="observation_name",
            display="Observation Name",
            mapping=lambda o: o.main_code.get("display", "")
            if isinstance(o.main_code, dict)
            else "",
            preview_value="Blood Pressure",
            description="Name of the observation",
        ),
        Field(
            key="observation_code",
            display="Observation Code",
            mapping=lambda o: o.main_code.get("code", "")
            if isinstance(o.main_code, dict)
            else "",
            preview_value="85354-9",
            description="LOINC or other standard code",
        ),
        Field(
            key="value",
            display="Value",
            mapping=lambda o: (
                str(o.value.get("value", ""))
                if isinstance(o.value, dict)
                else str(o.value)
                if o.value
                else ""
            ),
            preview_value="120/80",
            description="Observed value",
        ),
        Field(
            key="unit",
            display="Unit",
            mapping=lambda o: o.value.get("unit", "")
            if isinstance(o.value, dict)
            else "",
            preview_value="mmHg",
            description="Unit of measurement",
        ),
        Field(
            key="status",
            display="Status",
            mapping=lambda o: STATUS_DISPLAY.get(
                o.status, o.status.replace("_", " ").title() if o.status else ""
            ),
            preview_value="Final",
            description="Status of the observation",
        ),
        Field(
            key="interpretation",
            display="Interpretation",
            mapping=lambda o: o.interpretation.title() if o.interpretation else "",
            preview_value="Normal",
            description="Clinical interpretation",
        ),
        Field(
            key="effective_datetime",
            display="Recorded Date & Time",
            mapping=lambda o: format_datetime(o.effective_datetime)
            if o.effective_datetime
            else "",
            preview_value="10/01/2024 09:30 AM",
            description="When observation was taken",
        ),
        Field(
            key="note",
            display="Notes",
            mapping="note",
            preview_value="Patient at rest",
            description="Additional notes",
        ),
        Field(
            key="category",
            display="Category",
            mapping=lambda o: o.category.replace("_", " ").title()
            if o.category
            else "",
            preview_value="Vital Signs",
            description="Category of observation",
        ),
        Field(
            key="subject_type",
            display="Subject Type",
            mapping=lambda o: SUBJECT_TYPE_DISPLAY.get(
                o.subject_type, o.subject_type.title() if o.subject_type else ""
            ),
            preview_value="Patient",
            description="Type of subject (patient/encounter)",
        ),
        Field(
            key="subject_id",
            display="Subject ID",
            mapping=lambda o: str(o.subject_id) if o.subject_id else "",
            preview_value="",
            description="ID of the subject",
        ),
        Field(
            key="logged_by",
            display="Logged By",
            mapping=lambda o: o.data_entered_by.get_display_name()
            if o.data_entered_by
            else "",
            preview_value="Nurse Anjali Verma",
            description="Person who recorded this observation",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        if not encounter_id:
            raise ValueError(
                "encounter_id is required in context to build observations"
            )

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
        return "Observations"

    @classmethod
    def get_description(cls):
        return "Clinical observations and vital signs"


# Register the builder
contex_builder_registry.register("observations", ObservationContextBuilder)
