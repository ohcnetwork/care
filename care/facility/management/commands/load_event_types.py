from typing import TypedDict

from django.core.management import BaseCommand

from care.facility.models.events import EventType


class EventTypeDef(TypedDict, total=False):
    name: str
    model: str | None
    children: tuple["EventType", ...]
    fields: tuple[str, ...]


class Command(BaseCommand):
    """
    Management command to load event types
    """

    consultation_event_types: tuple[EventTypeDef, ...] = (
        {
            "name": "CONSULTATION",
            "model": "PatientConsultation",
            "children": (
                {
                    "name": "ENCOUNTER",
                    "children": (
                        {"name": "PATIENT_NO", "fields": ("patient_no",)},
                        {"name": "MEDICO_LEGAL_CASE", "fields": ("medico_legal_case",)},
                        {"name": "ROUTE_TO_FACILITY", "fields": ("route_to_facility",)},
                    ),
                },
                {
                    "name": "CLINICAL",
                    "children": (
                        {
                            "name": "DEATH",
                            "fields": ("death_datetime", "death_confirmed_doctor"),
                        },
                        {"name": "SUGGESTION", "fields": ("suggestion",)},
                        {"name": "CATEGORY", "fields": ("category",)},
                        {"name": "EXAMINATION", "fields": ("examination_details",)},
                        {
                            "name": "HISTORY_OF_PRESENT_ILLNESS",
                            "fields": ("history_of_present_illness",),
                        },
                        {"name": "TREATMENT_PLAN", "fields": ("treatment_plan",)},
                        {
                            "name": "CONSULTATION_NOTES",
                            "fields": ("consultation_notes",),
                        },
                        {
                            "name": "COURSE_IN_FACILITY",
                            "fields": ("course_in_facility",),
                        },
                        {
                            "name": "INVESTIGATION",
                            "fields": ("investigation",),
                        },
                        {
                            "name": "TREATING_PHYSICIAN",
                            "fields": (
                                "treating_physician__username",
                                "treating_physician__full_name",
                            ),
                        },
                    ),
                },
                {
                    "name": "HEALTH",
                    "children": (
                        {"name": "HEIGHT", "fields": ("height",)},
                        {"name": "WEIGHT", "fields": ("weight",)},
                    ),
                },
                {
                    "name": "INTERNAL_TRANSFER",
                    "children": (
                        {
                            "name": "DISCHARGE",
                            "fields": (
                                "discharge_date",
                                "discharge_reason",
                                "discharge_notes",
                            ),
                        },
                    ),
                },
            ),
        },
        {
            "name": "DAILY_ROUND",
            "model": "DailyRound",
            "children": (
                {
                    "name": "DAILY_ROUND_DETAILS",
                    "fields": (
                        "taken_at",
                        "round_type",
                        "other_details",
                        "action",
                        "review_after",
                    ),
                    "children": (
                        {
                            "name": "PHYSICAL_EXAMINATION",
                            "fields": ("physical_examination_info",),
                        },
                        {
                            "name": "PATIENT_CATEGORY",
                            "fields": ("patient_category",),
                        },
                    ),
                },
                {
                    "name": "VITALS",
                    "children": (
                        {"name": "TEMPERATURE", "fields": ("temperature",)},
                        {"name": "PULSE", "fields": ("pulse",)},
                        {"name": "BLOOD_PRESSURE", "fields": ("bp",)},
                        {"name": "RESPIRATORY_RATE", "fields": ("resp",)},
                        {"name": "RHYTHM", "fields": ("rhythm", "rhythm_detail")},
                        {"name": "PAIN_SCALE", "fields": ("pain_scale_enhanced",)},
                    ),
                },
                {
                    "name": "NEUROLOGICAL",
                    "fields": (
                        "left_pupil_size",
                        "left_pupil_size_detail",
                        "left_pupil_light_reaction",
                        "left_pupil_light_reaction_detail",
                        "right_pupil_size",
                        "right_pupil_size_detail",
                        "right_pupil_light_reaction",
                        "right_pupil_light_reaction_detail",
                        "glasgow_eye_open",
                        "glasgow_verbal_response",
                        "glasgow_motor_response",
                        "glasgow_total_calculated",
                        "limb_response_upper_extremity_left",
                        "limb_response_upper_extremity_right",
                        "limb_response_lower_extremity_left",
                        "limb_response_lower_extremity_right",
                        "consciousness_level",
                        "consciousness_level_detail",
                        "in_prone_position",
                    ),
                },
                {
                    "name": "RESPIRATORY_SUPPORT",
                    "fields": (
                        "bilateral_air_entry",
                        "etco2",
                        "ventilator_fio2",
                        "ventilator_interface",
                        "ventilator_mean_airway_pressure",
                        "ventilator_mode",
                        "ventilator_oxygen_modality",
                        "ventilator_oxygen_modality_flow_rate",
                        "ventilator_oxygen_modality_oxygen_rate",
                        "ventilator_peep",
                        "ventilator_pip",
                        "ventilator_pressure_support",
                        "ventilator_resp_rate",
                        "ventilator_spo2",
                        "ventilator_tidal_volume",
                    ),
                },
                {
                    "name": "ARTERIAL_BLOOD_GAS_ANALYSIS",
                    "fields": (
                        "base_excess",
                        "hco3",
                        "lactate",
                        "pco2",
                        "ph",
                        "po2",
                        "potassium",
                        "sodium",
                    ),
                },
                {
                    "name": "BLOOD_GLUCOSE",
                    "fields": (
                        "blood_sugar_level",
                        "insulin_intake_dose",
                        "insulin_intake_frequency",
                    ),
                },
                {
                    "name": "IO_BALANCE",
                    "children": (
                        {"name": "INFUSIONS", "fields": ("infusions",)},
                        {"name": "IV_FLUIDS", "fields": ("iv_fluids",)},
                        {"name": "FEEDS", "fields": ("feeds",)},
                        {"name": "OUTPUT", "fields": ("output",)},
                        {
                            "name": "TOTAL_INTAKE",
                            "fields": ("total_intake_calculated",),
                        },
                        {
                            "name": "TOTAL_OUTPUT",
                            "fields": ("total_output_calculated",),
                        },
                    ),
                },
                {
                    "name": "DIALYSIS",
                    "fields": (
                        "dialysis_fluid_balance",
                        "dialysis_net_balance",
                    ),
                    "children": (
                        {"name": "PRESSURE_SORE", "fields": ("pressure_sore",)},
                    ),
                },
                {"name": "NURSING", "fields": ("nursing",)},
                {
                    "name": "ROUTINE",
                    "children": (
                        {"name": "SLEEP_ROUTINE", "fields": ("sleep",)},
                        {"name": "BOWEL_ROUTINE", "fields": ("bowel_issue",)},
                        {
                            "name": "BLADDER_ROUTINE",
                            "fields": (
                                "bladder_drainage",
                                "bladder_issue",
                                "experiences_dysuria",
                                "urination_frequency",
                            ),
                        },
                        {
                            "name": "NUTRITION_ROUTINE",
                            "fields": ("nutrition_route", "oral_issue", "appetite"),
                        },
                    ),
                },
            ),
        },
        {
            "name": "PATIENT_NOTES",
            "model": "PatientNotes",
            "fields": ("note", "user_type"),
        },
        {
            "name": "DIAGNOSIS",
            "model": "ConsultationDiagnosis",
            "fields": ("diagnosis__label", "verification_status", "is_principal"),
        },
        {
            "name": "SYMPTOMS",
            "model": "EncounterSymptom",
            "fields": (
                "symptom",
                "other_symptom",
                "onset_date",
                "cure_date",
                "clinical_impression_status",
            ),
        },
    )

    inactive_event_types: tuple[str, ...] = (
        "RESPIRATORY",
        "INTAKE_OUTPUT",
        "VENTILATOR_MODES",
        "SYMPTOMS",
        "ROUND_SYMPTOMS",
        "SPO2",
    )

    def create_objects(
        self,
        types: tuple[EventType, ...],
        model: str | None = None,
        parent: EventType = None,
    ):
        for event_type in types:
            model = event_type.get("model", model)
            obj, _ = EventType.objects.update_or_create(
                name=event_type["name"],
                defaults={
                    "parent": parent,
                    "model": model,
                    "fields": event_type.get("fields", []),
                    "is_active": True,
                },
            )
            if children := event_type.get("children"):
                self.create_objects(children, model, obj)

    def handle(self, *args, **options):
        self.stdout.write("Loading Event Types... ", ending="")

        EventType.objects.filter(name__in=self.inactive_event_types).update(
            is_active=False
        )

        self.create_objects(self.consultation_event_types)

        self.stdout.write(self.style.SUCCESS("OK"))
