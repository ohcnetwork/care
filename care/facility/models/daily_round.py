import enum

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import JSONField
from django.shortcuts import get_object_or_404
from multiselectfield import MultiSelectField
from multiselectfield.utils import get_max_length

from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    PatientBaseModel,
)
from care.facility.models.base import covert_choice_dict
from care.facility.models.bed import AssetBed
from care.facility.models.json_schema.daily_round import (
    BLOOD_PRESSURE,
    FEED,
    INFUSIONS,
    IV_FLUID,
    META,
    NURSING_PROCEDURE,
    OUTPUT,
    PAIN_SCALE_ENHANCED,
    PRESSURE_SORE,
)
from care.facility.models.patient_base import CURRENT_HEALTH_CHOICES, SYMPTOM_CHOICES
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import User
from care.utils.models.validators import JSONFieldSchemaValidator


class DailyRound(PatientBaseModel):
    class RoundsType(enum.Enum):
        NORMAL = 0
        VENTILATOR = 100
        ICU = 200
        AUTOMATED = 300
        TELEMEDICINE = 400

    RoundsTypeChoice = [(e.value, e.name) for e in RoundsType]
    RoundsTypeDict = covert_choice_dict(RoundsTypeChoice)

    class ConsciousnessType(enum.Enum):
        UNKNOWN = 0
        ALERT = 5
        RESPONDS_TO_VOICE = 10
        RESPONDS_TO_PAIN = 15
        UNRESPONSIVE = 20
        AGITATED_OR_CONFUSED = 25
        ONSET_OF_AGITATION_AND_CONFUSION = 30

    ConsciousnessChoice = [(e.value, e.name) for e in ConsciousnessType]

    class PupilReactionType(enum.Enum):
        UNKNOWN = 0
        BRISK = 5
        SLUGGISH = 10
        FIXED = 15
        CANNOT_BE_ASSESSED = 20

    PupilReactionChoice = [(e.value, e.name) for e in PupilReactionType]

    class LimbResponseType(enum.Enum):
        UNKNOWN = 0
        STRONG = 5
        MODERATE = 10
        WEAK = 15
        FLEXION = 20
        EXTENSION = 25
        NONE = 30

    LimbResponseChoice = [(e.value, e.name) for e in LimbResponseType]

    class RythmnType(enum.Enum):
        UNKNOWN = 0
        REGULAR = 5
        IRREGULAR = 10

    RythmnChoice = [(e.value, e.name) for e in RythmnType]

    class VentilatorInterfaceType(enum.Enum):
        UNKNOWN = 0
        INVASIVE = 5
        NON_INVASIVE = 10
        OXYGEN_SUPPORT = 15

    VentilatorInterfaceChoice = [(e.value, e.name) for e in VentilatorInterfaceType]

    class VentilatorModeType(enum.Enum):
        UNKNOWN = 0
        VCV = 5
        PCV = 10
        PRVC = 15
        APRV = 20
        VC_SIMV = 25
        PC_SIMV = 30
        PRVC_SIMV = 40
        ASV = 45
        PSV = 50

    VentilatorModeChoice = [(e.value, e.name) for e in VentilatorModeType]

    class VentilatorOxygenModalityType(enum.Enum):
        UNKNOWN = 0
        NASAL_PRONGS = 5
        SIMPLE_FACE_MASK = 10
        NON_REBREATHING_MASK = 15
        HIGH_FLOW_NASAL_CANNULA = 20

    VentilatorOxygenModalityChoice = [
        (e.value, e.name) for e in VentilatorOxygenModalityType
    ]

    class InsulinIntakeFrequencyType(enum.Enum):
        UNKNOWN = 0
        OD = 5
        BD = 10
        TD = 15

    InsulinIntakeFrequencyChoice = [
        (e.value, e.name) for e in InsulinIntakeFrequencyType
    ]

    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
        related_name="daily_rounds",
    )
    temperature = models.DecimalField(
        decimal_places=2,
        max_digits=5,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(95), MaxValueValidator(106)],
    )
    spo2 = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True, default=None
    )
    temperature_measured_at = models.DateTimeField(null=True, blank=True)
    physical_examination_info = models.TextField(null=True, blank=True)
    additional_symptoms = MultiSelectField(
        choices=SYMPTOM_CHOICES,
        default=1,
        null=True,
        blank=True,
        max_length=get_max_length(SYMPTOM_CHOICES, None),
    )
    other_symptoms = models.TextField(default="", blank=True)
    deprecated_covid_category = models.CharField(
        choices=COVID_CATEGORY_CHOICES,
        max_length=8,
        default=None,
        blank=True,
        null=True,
    )  # Deprecated
    patient_category = models.CharField(
        choices=CATEGORY_CHOICES, max_length=8, blank=False, null=True
    )
    current_health = models.IntegerField(
        default=0, choices=CURRENT_HEALTH_CHOICES, blank=True
    )
    other_details = models.TextField(null=True, blank=True)
    medication_given = JSONField(default=dict)  # To be Used Later on

    last_updated_by_telemedicine = models.BooleanField(default=False)
    created_by_telemedicine = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="update_created_user",
    )

    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="update_last_edited_user",
    )

    taken_at = models.DateTimeField(null=True, blank=True, db_index=True)

    rounds_type = models.IntegerField(
        choices=RoundsTypeChoice, default=RoundsType.NORMAL.value
    )
    is_parsed_by_ocr = models.BooleanField(default=False)

    # Critical Care Attributes

    consciousness_level = models.IntegerField(
        choices=ConsciousnessChoice, default=None, null=True
    )
    consciousness_level_detail = models.TextField(default=None, null=True, blank=True)

    in_prone_position = models.BooleanField(default=None, null=True, blank=True)

    left_pupil_size = models.IntegerField(
        default=None,
        null=True,
        verbose_name="Left Pupil Size",
        validators=[MinValueValidator(0), MaxValueValidator(8)],
    )
    left_pupil_size_detail = models.TextField(default=None, null=True, blank=True)
    left_pupil_light_reaction = models.IntegerField(
        choices=PupilReactionChoice, default=None, null=True
    )
    left_pupil_light_reaction_detail = models.TextField(
        default=None, null=True, blank=True
    )
    right_pupil_size = models.IntegerField(
        default=None,
        null=True,
        verbose_name="Right Pupil Size",
        validators=[MinValueValidator(0), MaxValueValidator(8)],
    )
    right_pupil_size_detail = models.TextField(default=None, null=True, blank=True)
    right_pupil_light_reaction = models.IntegerField(
        choices=PupilReactionChoice, default=None, null=True
    )
    right_pupil_light_reaction_detail = models.TextField(
        default=None, null=True, blank=True
    )
    glasgow_eye_open = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )
    glasgow_verbal_response = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    glasgow_motor_response = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
    )
    glasgow_total_calculated = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(3), MaxValueValidator(15)],
    )
    limb_response_upper_extremity_right = models.IntegerField(
        choices=LimbResponseChoice, default=None, null=True
    )
    limb_response_upper_extremity_left = models.IntegerField(
        choices=LimbResponseChoice, default=None, null=True
    )
    limb_response_lower_extremity_left = models.IntegerField(
        choices=LimbResponseChoice, default=None, null=True
    )
    limb_response_lower_extremity_right = models.IntegerField(
        choices=LimbResponseChoice, default=None, null=True
    )
    bp = JSONField(default=dict, validators=[JSONFieldSchemaValidator(BLOOD_PRESSURE)])
    pulse = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(200)],
    )
    resp = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
    )
    rhythm = models.IntegerField(choices=RythmnChoice, default=None, null=True)
    rhythm_detail = models.TextField(default=None, null=True, blank=True)
    ventilator_interface = models.IntegerField(
        choices=VentilatorInterfaceChoice,
        default=None,
        null=True,
    )
    ventilator_mode = models.IntegerField(
        choices=VentilatorModeChoice, default=None, null=True
    )
    ventilator_peep = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
    )
    ventilator_pip = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    ventilator_mean_airway_pressure = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
    )
    ventilator_resp_rate = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    ventilator_pressure_support = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
    )
    ventilator_tidal_volume = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
    )
    ventilator_oxygen_modality = models.IntegerField(
        choices=VentilatorOxygenModalityChoice, default=None, null=True
    )
    ventilator_oxygen_modality_oxygen_rate = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
    )
    ventilator_oxygen_modality_flow_rate = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
    )
    ventilator_fi02 = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(21), MaxValueValidator(100)],
    )
    ventilator_spo2 = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    etco2 = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(200)],
    )
    bilateral_air_entry = models.BooleanField(default=None, null=True, blank=True)
    pain = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    pain_scale_enhanced = JSONField(
        default=list,
        validators=[JSONFieldSchemaValidator(PAIN_SCALE_ENHANCED)],
    )
    ph = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    pco2 = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(10), MaxValueValidator(200)],
    )
    po2 = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(10), MaxValueValidator(400)],
    )
    hco3 = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(5), MaxValueValidator(80)],
    )
    base_excess = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(-20), MaxValueValidator(20)],
    )
    lactate = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    sodium = models.DecimalField(
        decimal_places=2,
        max_digits=5,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(100), MaxValueValidator(170)],
    )
    potassium = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    blood_sugar_level = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(700)],
    )
    insulin_intake_dose = models.DecimalField(
        decimal_places=2,
        max_digits=5,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    insulin_intake_frequency = models.IntegerField(
        choices=InsulinIntakeFrequencyChoice,
        default=None,
        null=True,
    )
    infusions = JSONField(
        default=list, validators=[JSONFieldSchemaValidator(INFUSIONS)]
    )
    iv_fluids = JSONField(default=list, validators=[JSONFieldSchemaValidator(IV_FLUID)])
    feeds = JSONField(default=list, validators=[JSONFieldSchemaValidator(FEED)])
    total_intake_calculated = models.DecimalField(
        decimal_places=2, max_digits=6, blank=True, default=None, null=True
    )
    output = JSONField(default=list, validators=[JSONFieldSchemaValidator(OUTPUT)])
    total_output_calculated = models.DecimalField(
        decimal_places=2, max_digits=6, blank=True, default=None, null=True
    )
    dialysis_fluid_balance = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5000)],
    )
    dialysis_net_balance = models.IntegerField(
        default=None,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5000)],
    )
    pressure_sore = JSONField(
        default=list, validators=[JSONFieldSchemaValidator(PRESSURE_SORE)]
    )
    nursing = JSONField(
        default=list, validators=[JSONFieldSchemaValidator(NURSING_PROCEDURE)]
    )

    medicine_administration = JSONField(
        default=list,
    )

    meta = JSONField(default=dict, validators=[JSONFieldSchemaValidator(META)])

    def cztn(self, value):
        """
        Cast Zero to null values
        """
        if not value:
            return 0
        return value

    def update_pressure_sore(self):
        area_interval_points = [
            0.1,
            0.3,
            0.7,
            1.1,
            2.1,
            3.1,
            4.1,
            8.1,
            12.1,
            25,
        ]
        exudate_amounts = ["None", "Light", "Moderate", "Heavy"]
        tissue_types = [
            "Closed",
            "Epithelial",
            "Granulation",
            "Slough",
            "Necrotic",
        ]

        def cal_push_score(item):
            push_score = item.get("base_score", 0.0)
            area_score = 0
            area = item["length"] * item["width"]
            push_score += exudate_amounts.index(item["exudate_amount"])
            push_score += tissue_types.index(item["tissue_type"])
            for point in area_interval_points:
                if area >= point:
                    area_score += 1
            push_score += area_score
            return push_score

        def set_push_score(item):
            item["push_score"] = cal_push_score(item)
            return item

        return list(map(set_push_score, self.pressure_sore))

    def save(self, *args, **kwargs):
        # Calculate all automated columns and populate them
        if (
            self.glasgow_eye_open is not None
            and self.glasgow_motor_response is not None
            and self.glasgow_verbal_response is not None
        ):
            self.glasgow_total_calculated = (
                self.cztn(self.glasgow_eye_open)
                + self.cztn(self.glasgow_motor_response)
                + self.cztn(self.glasgow_verbal_response)
            )
        if (
            self.infusions is not None
            and self.iv_fluids is not None
            and self.feeds is not None
        ):
            self.total_intake_calculated = sum([x["quantity"] for x in self.infusions])
            self.total_intake_calculated += sum([x["quantity"] for x in self.iv_fluids])
            self.total_intake_calculated += sum([x["quantity"] for x in self.feeds])

        if self.output is not None:
            self.total_output_calculated = sum([x["quantity"] for x in self.output])

        super(DailyRound, self).save(*args, **kwargs)

    @staticmethod
    def has_read_permission(request):
        if request.user.user_type < User.TYPE_VALUE_MAP["NurseReadOnly"]:
            return False

        consultation = get_object_or_404(
            PatientConsultation,
            external_id=request.parser_context["kwargs"]["consultation_external_id"],
        )
        return request.user.is_superuser or (
            (request.user in consultation.patient.facility.users.all())
            or (
                request.user == consultation.assigned_to
                or request.user == consultation.patient.assigned_to
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (request.user.district == consultation.patient.facility.district)
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (request.user.state == consultation.patient.facility.state)
            )
        )

    @staticmethod
    def has_write_permission(request):
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and DailyRound.has_read_permission(request)
        )

    @staticmethod
    def has_analyse_permission(request):
        return DailyRound.has_read_permission(request)

    def has_object_read_permission(self, request):
        if request.user.user_type < User.TYPE_VALUE_MAP["NurseReadOnly"]:
            return False

        return (
            request.user.is_superuser
            or (
                self.consultation.patient.facility
                and request.user in self.consultation.patient.facility.users.all()
            )
            or (
                self.consultation.assigned_to == request.user
                or request.user == self.consultation.patient.assigned_to
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.district
                    == self.consultation.patient.facility.district
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.state
                    == self.consultation.patient.facility.district
                )
            )
        )

    def has_object_write_permission(self, request):
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and self.has_object_read_permission(request)
        )

    def has_object_asset_read_permission(self, request):
        return False

    def has_object_asset_write_permission(self, request):
        consultation = PatientConsultation.objects.select_related(
            "current_bed__bed"
        ).get(external_id=request.parser_context["kwargs"]["consultation_external_id"])
        return AssetBed.objects.filter(
            asset=request.user.asset, bed=consultation.current_bed.bed
        ).exists()
