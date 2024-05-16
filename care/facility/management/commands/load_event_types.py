from typing import Optional, Tuple, TypedDict

from django.core.management import BaseCommand

from care.facility.models.events import EventType


class EventTypeDef(TypedDict, total=False):
    name: str
    model: Optional[str]
    children: Tuple["EventType", ...]
    fields: Tuple[str, ...]


class Command(BaseCommand):
    """
    Management command to load event types
    """

    consultation_event_types: Tuple[EventTypeDef, ...] = (
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
                            "name": "SYMPTOMS",
                            "fields": (
                                "symptoms",
                                "other_symptoms",
                                "symptoms_onset_date",
                            ),
                        },
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
                            "name": "TREATING_PHYSICIAN",
                            "fields": ("treating_physician",),
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
                    "name": "HEALTH",
                    "children": (
                        {
                            "name": "ROUND_SYMPTOMS",  # todo resolve clash with consultation symptoms
                            "fields": ("additional_symptoms", "other_symptoms"),
                        },
                        {
                            "name": "PHYSICAL_EXAMINATION",
                            "fields": ("physical_examination_info",),
                        },
                        {"name": "PATIENT_CATEGORY", "fields": ("patient_category",)},
                    ),
                },
                {
                    "name": "VITALS",
                    "children": (
                        {
                            "name": "TEMPERATURE",
                            "fields": (
                                "temperature",
                                "temperature_measured_at",  # todo remove field
                            ),
                        },
                        {"name": "SPO2", "fields": ("spo2",)},
                        {"name": "PULSE", "fields": ("pulse",)},
                        {"name": "BLOOD_PRESSURE", "fields": ("bp",)},
                        {"name": "RESPIRATORY_RATE", "fields": ("resp",)},
                        {"name": "RHYTHM", "fields": ("rhythm", "rhythm_details")},
                    ),
                },
                {
                    "name": "RESPIRATORY",
                    "children": (
                        {
                            "name": "BILATERAL_AIR_ENTRY",
                            "fields": ("bilateral_air_entry",),
                        },
                    ),
                },
                {
                    "name": "INTAKE_OUTPUT",
                    "children": (
                        {"name": "INFUSIONS", "fields": ("infusions",)},
                        {"name": "IV_FLUIDS", "fields": ("iv_fluids",)},
                        {"name": "FEEDS", "fields": ("feeds",)},
                        {
                            "name": "TOTAL_INTAKE",
                            "fields": ("total_intake_calculated",),
                        },
                        {"name": "OUTPUT", "fields": ("output",)},
                        {
                            "name": "TOTAL_OUTPUT",
                            "fields": ("total_output_calculated",),
                        },
                    ),
                },
                {
                    "name": "VENTILATOR_MODES",
                    "fields": (
                        "ventilator_interface",
                        "ventilator_mode",
                        "ventilator_peep",
                        "ventilator_pip",
                        "ventilator_mean_airway_pressure",
                        "ventilator_resp_rate",
                        "ventilator_pressure_support",
                        "ventilator_tidal_volume",
                        "ventilator_oxygen_modality",
                        "ventilator_oxygen_modality_oxygen_rate",
                        "ventilator_oxygen_modality_flow_rate",
                        "ventilator_fi02",
                        "ventilator_spo2",
                    ),
                },
                {
                    "name": "DIALYSIS",
                    "fields": (
                        "pressure_sore",
                        "dialysis_fluid_balance",
                        "dialysis_net_balance",
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
                        "limb_response_upper_extremity_right",
                        "limb_response_upper_extremity_left",
                        "limb_response_lower_extremity_left",
                        "limb_response_lower_extremity_right",
                        "consciousness_level",
                        "consciousness_level_detail",
                    ),
                },
                {
                    "name": "BLOOD_GLUCOSE",
                    "fields": ("blood_sugar_level",),
                },
                {
                    "name": "DAILY_ROUND_DETAILS",
                    "fields": (
                        "other_details",
                        "medication_given",
                        "in_prone_position",
                        "etco2",
                        "pain",
                        "pain_scale_enhanced",
                        "ph",
                        "pco2",
                        "po2",
                        "hco3",
                        "base_excess",
                        "lactate",
                        "sodium",
                        "potassium",
                        "insulin_intake_dose",
                        "insulin_intake_frequency",
                        "nursing",
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
            "fields": ("diagnosis", "verification_status", "is_principal"),
        },
    )

    def create_objects(
        self, types: Tuple[EventType, ...], model: str = None, parent: EventType = None
    ):
        for event_type in types:
            model = event_type.get("model", model)
            obj, _ = EventType.objects.update_or_create(
                name=event_type["name"],
                defaults={
                    "parent": parent,
                    "model": model,
                    "fields": event_type.get("fields", []),
                },
            )
            if children := event_type.get("children"):
                self.create_objects(children, model, obj)

    def handle(self, *args, **options):
        self.stdout.write("Loading Event Types... ", ending="")

        self.create_objects(self.consultation_event_types)

        self.stdout.write(self.style.SUCCESS("OK"))
