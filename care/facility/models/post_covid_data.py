# change on delete to protect
from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField
from care.facility.models.base import BaseModel
import enum


class PostCovidTime(enum.Enum):
    UNDER_THREE_WEEKS = 1
    THREE_TO_TWELVE = 2
    OVER_TWELVE_WEEKS = 3


PostCovidTimeChoices = [(e.value, e.name) for e in PostCovidTime]


class CovidCategory(enum.Enum):
    MILD = 1
    MODERATE = 2
    SEVERE = 3


CovidCategoryChoices = [(e.value, e.name) for e in CovidCategory]


class OxygenType(enum.Enum):
    NASAL_PRONGS = 1
    FACE_MASK = 2
    NRBM = 3
    FNO = 4


OxygenTypeChoices = [(e.value, e.name) for e in OxygenType]


class AnticoagulantModeOfTransmission(enum.Enum):
    IV = 1
    ORAL = 2


AnticoagulantModeOfTransmissionChoices = [
    (e.value, e.name) for e in AnticoagulantModeOfTransmission
]


class PostCovidData(BaseModel):
    # Do we have to delete post covid data of patient if patient is deleted
    patient = models.ForeignKey(
        "PatientRegistration",
        on_delete=models.PROTECT,
        null=True
    )
    date_of_onset_symptoms = models.DateField(
        default=None,
        null=True,
        verbose_name="Date of first appearance of symptoms"
    )
    post_covid_time = models.IntegerField(
        choices=PostCovidTimeChoices,
        default=1,
        blank=False
    )
    date_of_test_positive = models.DateField(
        default=None,
        null=False,
        blank=False,
        verbose_name="date when patient was tested positive"
    )
    date_of_test_negative = models.DateField(
        default=None,
        null=False,
        blank=False,
        verbose_name="date when patient was tested negative"
    )

    testing_centre = models.TextField(default="", null=True)
    pre_covid_comorbidities = JSONField(
        default=dict,
        null=True,
        verbose_name="diseases before coronavirus"
    )
    post_covid_comorbidities = JSONField(
        default=dict,
        null=True,
        verbose_name="diseases after coronavirus"
    )

    treatment_facility = models.ManyToManyField(
        "Facility",
        null=True
    )
    treatment_duration = models.IntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name="Number of days for which treatment last"
    )
    covid_category = models.IntegerField(
        choices=CovidCategoryChoices,
        blank=False
    )

    vitals_at_admission = JSONField(default=dict, null=True)

    condition_on_admission = models.TextField(default="", null=True)
    condition_on_discharge = models.TextField(default="", null=True)
    icu_admission = models.BooleanField(default=False, null=False, blank=False)
    oxygen_requirement = models.BooleanField(default=False, null=False, blank=False)

    oxygen_requirement_detail = models.IntegerField(
        choices=OxygenTypeChoices, default=1
    )

    mechanical_ventiltions_niv = models.IntegerField(default=0, null=True)
    mechanical_ventiltions_invasive = models.IntegerField(default=0, null=True)
    antivirals = models.BooleanField(default=False, null=False)

    antivirals_drugs = ArrayField(
        JSONField(default=dict, null=True),
        default=list,
        null=True
    )
    steroids = models.BooleanField(default=False, null=True)
    steroids_drugs = ArrayField(
        JSONField(default=dict, null=False),
        default=list,
        null=True
    )

    anticoagulants = models.BooleanField(default=False, null=True)
    anticoagulants_drugs = ArrayField(
        JSONField(default=dict, null=False),
        default=list,
        null=True
    )

    antibiotics = models.BooleanField(default=False, null=True)
    antibiotics_drugs = ArrayField(
        JSONField(default=dict, null=False),
        default=list,
        null=True
    )

    antifungals = models.BooleanField(default=False, null=True)
    antifungals_drugs = ArrayField(
        JSONField(default=dict, null=False),
        default=list,
        null=True
    )

    documented_secondary_bacterial_infection = models.TextField(
        default="",
        null=True,
        verbose_name="any bacterial infection during treatment"
    )
    documented_fungal_infection = models.TextField(
        default="",
        null=True,
        verbose_name="any fungal infection during treatment"
    )
    newly_detected_comorbidities = models.TextField(
        default="",
        null=True,
        verbose_name="any new disease"
    )
    worsening_of_comorbidities = models.TextField(
        default="",
        null=True,
        verbose_name="is any disease worsened during treatment"
    )
    at_present_symptoms = ArrayField(
        models.CharField(default="", null=False, max_length=100),
        default=dict,
        null=False,
        blank=False
    )

    on_examination_vitals = JSONField(default=dict, null=True, blank=False)
    appearance_of_pallor = models.BooleanField(default=False, null=True)
    appearance_of_cyanosis = models.BooleanField(default=False, null=True)
    appearance_of_pedal_edema = models.BooleanField(default=False, null=True)
    appearance_of_pedal_edema_details = models.TextField(default="", null=True)

    systemic_examination = JSONField(
        default=dict,
        null=True,
        verbose_name="examinations of central nervous system"
    )

    single_breath_count = models.TextField(default="", null=True)
    six_minute_walk_test = models.TextField(default="", null=True)
    concurrent_medications = models.TextField(default="", null=True)
    probable_diagnosis = models.TextField(default="", null=False, blank=False)
