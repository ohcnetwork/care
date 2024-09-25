from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import JSONField
from django.shortcuts import get_object_or_404

from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    PatientBaseModel,
)
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
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import User
from care.utils.models.validators import JSONFieldSchemaValidator


class DailyRound(PatientBaseModel):
    class RoundsType(models.IntegerChoices):
        NORMAL = 0, "NORMAL"
        COMMUNITY_NURSES_LOG = 30, "COMMUNITY_NURSES_LOG"
        DOCTORS_LOG = 50, "DOCTORS_LOG"
        VENTILATOR = 100, "VENTILATOR"
        ICU = 200, "ICU"
        AUTOMATED = 300, "AUTOMATED"
        TELEMEDICINE = 400, "TELEMEDICINE"

    class ConsciousnessTypeChoice(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        ALERT = 5, "ALERT"
        RESPONDS_TO_VOICE = 10, "RESPONDS_TO_VOICE"
        RESPONDS_TO_PAIN = 15, "RESPONDS_TO_PAIN"
        UNRESPONSIVE = 20, "UNRESPONSIVE"
        AGITATED_OR_CONFUSED = 25, "AGITATED_OR_CONFUSED"
        ONSET_OF_AGITATION_AND_CONFUSION = 30, "ONSET_OF_AGITATION_AND_CONFUSION"

    class BowelDifficultyType(models.IntegerChoices):
        NO_DIFFICULTY = 0, "NO_DIFFICULTY"
        CONSTIPATION = 1, "CONSTIPATION"
        DIARRHOEA = 2, "DIARRHOEA"

    class BladderDrainageType(models.IntegerChoices):
        NORMAL = 1, "NORMAL"
        CONDOM_CATHETER = 2, "CONDOM_CATHETER"
        DIAPER = 3, "DIAPER"
        INTERMITTENT_CATHETER = 4, "INTERMITTENT_CATHETER"
        CONTINUOUS_INDWELLING_CATHETER = 5, "CONTINUOUS_INDWELLING_CATHETER"
        CONTINUOUS_SUPRAPUBIC_CATHETER = 6, "CONTINUOUS_SUPRAPUBIC_CATHETER"
        UROSTOMY = 7, "UROSTOMY"

    class BladderIssueType(models.IntegerChoices):
        NO_ISSUES = 0, "NO_ISSUES"
        INCONTINENCE = 1, "INCONTINENCE"
        RETENTION = 2, "RETENTION"
        HESITANCY = 3, "HESITANCY"

    class UrinationFrequencyType(models.IntegerChoices):
        NORMAL = 1, "NORMAL"
        DECREASED = 2, "DECREASED"
        INCREASED = 3, "INCREASED"

    class SleepType(models.IntegerChoices):
        EXCESSIVE = 1, "EXCESSIVE"
        SATISFACTORY = 2, "SATISFACTORY"
        UNSATISFACTORY = 3, "UNSATISFACTORY"
        NO_SLEEP = 4, "NO_SLEEP"

    class NutritionRouteType(models.IntegerChoices):
        ORAL = 1, "ORAL"
        RYLES_TUBE = 2, "RYLES_TUBE"
        GASTROSTOMY_OR_JEJUNOSTOMY = 3, "GASTROSTOMY_OR_JEJUNOSTOMY"
        PEG = 4, "PEG"
        PARENTERAL_TUBING_FLUID = 5, "PARENTERAL_TUBING_FLUID"
        PARENTERAL_TUBING_TPN = 6, "PARENTERAL_TUBING_TPN"

    class OralIssueType(models.IntegerChoices):
        NO_ISSUE = 0, "NO_ISSUE"
        DYSPHAGIA = 1, "DYSPHAGIA"
        ODYNOPHAGIA = 2, "ODYNOPHAGIA"

    class AppetiteType(models.IntegerChoices):
        INCREASED = 1, "INCREASED"
        SATISFACTORY = 2, "SATISFACTORY"
        REDUCED = 3, "REDUCED"
        NO_TASTE_FOR_FOOD = 4, "NO_TASTE_FOR_FOOD"
        CANNOT_BE_ASSESSED = 5, "CANNOT_BE_ASSESSED"

    class PupilReactionType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        BRISK = 5, "BRISK"
        SLUGGISH = 10, "SLUGGISH"
        FIXED = 15, "FIXED"
        CANNOT_BE_ASSESSED = 20, "CANNOT_BE_ASSESSED"

    class LimbResponseType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        STRONG = 5, "STRONG"
        MODERATE = 10, "MODERATE"
        WEAK = 15, "WEAK"
        FLEXION = 20, "FLEXION"
        EXTENSION = 25, "EXTENSION"
        NONE = 30, "NONE"

    class RythmnType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        REGULAR = 5, "REGULAR"
        IRREGULAR = 10, "IRREGULAR"

    class VentilatorInterfaceType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        INVASIVE = 5, "INVASIVE"
        NON_INVASIVE = 10, "NON_INVASIVE"
        OXYGEN_SUPPORT = 15, "OXYGEN_SUPPORT"

    class VentilatorModeType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        VCV = 5, "VCV"
        PCV = 10, "PCV"
        PRVC = 15, "PRVC"
        APRV = 20, "APRV"
        VC_SIMV = 25, "VC_SIMV"
        PC_SIMV = 30, "PC_SIMV"
        PRVC_SIMV = 40, "PRVC_SIMV"
        ASV = 45, "ASV"
        PSV = 50, "PSV"

    class VentilatorOxygenModalityType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        NASAL_PRONGS = 5, "NASAL_PRONGS"
        SIMPLE_FACE_MASK = 10, "SIMPLE_FACE_MASK"
        NON_REBREATHING_MASK = 15, "NON_REBREATHING_MASK"
        HIGH_FLOW_NASAL_CANNULA = 20, "HIGH_FLOW_NASAL_CANNULA"

    class InsulinIntakeFrequencyType(models.IntegerChoices):
        UNKNOWN = 0, "UNKNOWN"
        OD = 5, "OD"
        BD = 10, "BD"
        TD = 15, "TD"

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
        validators=[MinValueValidator(Decimal(95)), MaxValueValidator(Decimal(106))],
    )
    archived_spo2 = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True, default=None
    )  # Deprecated
    physical_examination_info = models.TextField(null=True, blank=True)
    deprecated_covid_category = models.CharField(
        choices=COVID_CATEGORY_CHOICES,
        max_length=8,
        default=None,
        blank=True,
        null=True,
    )  # Deprecated
    patient_category = models.CharField(
        choices=CATEGORY_CHOICES, max_length=13, blank=False, null=True
    )
    other_details = models.TextField(null=True, blank=True)

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
        choices=RoundsType.choices, default=RoundsType.NORMAL.value
    )
    is_parsed_by_ocr = models.BooleanField(default=False)

    # Community Nurse's Log Attributes

    bowel_issue = models.SmallIntegerField(
        choices=BowelDifficultyType.choices, default=None, null=True, blank=True
    )
    bladder_drainage = models.SmallIntegerField(
        choices=BladderDrainageType.choices, default=None, null=True, blank=True
    )
    bladder_issue = models.SmallIntegerField(
        choices=BladderIssueType.choices, default=None, null=True, blank=True
    )
    is_experiencing_dysuria = models.BooleanField(default=None, null=True, blank=True)
    urination_frequency = models.SmallIntegerField(
        choices=UrinationFrequencyType.choices, default=None, null=True, blank=True
    )
    sleep = models.SmallIntegerField(
        choices=SleepType.choices, default=None, null=True, blank=True
    )
    nutrition_route = models.SmallIntegerField(
        choices=NutritionRouteType.choices, default=None, null=True, blank=True
    )
    oral_issue = models.SmallIntegerField(
        choices=OralIssueType.choices, default=None, null=True, blank=True
    )
    appetite = models.SmallIntegerField(
        choices=AppetiteType.choices, default=None, null=True, blank=True
    )

    # Critical Care Attributes

    consciousness_level = models.IntegerField(
        choices=ConsciousnessTypeChoice.choices, default=None, null=True
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
        choices=PupilReactionType.choices, default=None, null=True
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
        choices=PupilReactionType.choices, default=None, null=True
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
        choices=LimbResponseType.choices, default=None, null=True
    )
    limb_response_upper_extremity_left = models.IntegerField(
        choices=LimbResponseType.choices, default=None, null=True
    )
    limb_response_lower_extremity_left = models.IntegerField(
        choices=LimbResponseType.choices, default=None, null=True
    )
    limb_response_lower_extremity_right = models.IntegerField(
        choices=LimbResponseType.choices, default=None, null=True
    )
    bp = JSONField(
        default=None, validators=[JSONFieldSchemaValidator(BLOOD_PRESSURE)], null=True
    )
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
    rhythm = models.IntegerField(choices=RythmnType.choices, default=None, null=True)
    rhythm_detail = models.TextField(default=None, null=True, blank=True)
    ventilator_interface = models.IntegerField(
        choices=VentilatorInterfaceType.choices,
        default=None,
        null=True,
    )
    ventilator_mode = models.IntegerField(
        choices=VentilatorModeType.choices, default=None, null=True
    )
    ventilator_peep = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(30))],
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
        choices=VentilatorOxygenModalityType.choices, default=None, null=True
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
    ventilator_fio2 = models.IntegerField(
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
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(10))],
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
        validators=[MinValueValidator(Decimal(5)), MaxValueValidator(Decimal(80))],
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
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(20))],
    )
    sodium = models.DecimalField(
        decimal_places=2,
        max_digits=5,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(Decimal(100)), MaxValueValidator(Decimal(170))],
    )
    potassium = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        blank=True,
        default=None,
        null=True,
        validators=[MinValueValidator(Decimal(1)), MaxValueValidator(Decimal(10))],
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
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(100))],
    )
    insulin_intake_frequency = models.IntegerField(
        choices=InsulinIntakeFrequencyType.choices,
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
        Cast null to zero values
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

        super().save(*args, **kwargs)

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
                request.user
                in (consultation.assigned_to, consultation.patient.assigned_to)
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
                request.user
                in (
                    self.consultation.assigned_to,
                    self.consultation.patient.assigned_to,
                )
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
                    and request.user.state == self.consultation.patient.facility.state
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
