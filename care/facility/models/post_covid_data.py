from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField
from care.facility.models.base import BaseModel
from care.facility.models.patient_consultation import PatientConsultation
import enum


class CovidCategory(enum.Enum):
    MILD = "Mild"
    MODERATE = "Moderate"
    SEVERE = "Severe"


CovidCategoryChoices = [(e.value, e.name) for e in CovidCategory]


class OxygenType(enum.Enum):
    NASAL_PRONGS = "Nasal prongs"
    FACE_MASK = "Face mask"
    NRBM = "Nrbm"
    FNO = "Fno"


OxygenTypeChoices = [(e.value, e.name) for e in OxygenType]


class PostCovidData(BaseModel):
    consultation = models.OneToOneField(
        PatientConsultation,
        on_delete=models.PROTECT,
        null=False
    )
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
    covid_category = models.CharField(
        choices=CovidCategoryChoices,
        blank=True, null=True
    )

    vitals_at_admission = JSONField(default=dict, null=True)

    condition_on_admission = models.TextField(default="", null=True, blank=True)
    condition_on_discharge = models.TextField(default="", null=True, blank=True)
    icu_admission = models.BooleanField(default=False, null=False, blank=False)
    oxygen_requirement = models.BooleanField(default=False, null=False, blank=False)

    oxygen_requirement_detail = models.CharField(
        choices=OxygenTypeChoices, default=OxygenType.NASAL_PRONGS, max_length=15,
        null=True, blank=True
    )

    mechanical_ventilations_niv = models.IntegerField(default=0, null=True)
    mechanical_ventilations_invasive = models.IntegerField(default=0, null=True)
    antivirals = models.BooleanField(default=False, null=False)

    antivirals_drugs = JSONField(
        models.CharField(max_length=100),
        default=list,
        null=True,
        blank=True
    )
    steroids = models.BooleanField(default=False, null=True)
    steroids_drugs = JSONField(
        default=list,
        null=True,
        blank=True
    )

    anticoagulants = models.BooleanField(default=False, null=True)
    anticoagulants_drugs = JSONField(
        JSONField(default=dict, null=False),
        default=list,
        null=True,
        blank=True
    )

    antibiotics = models.BooleanField(default=False, null=True)
    antibiotics_drugs = JSONField(
        default=list,
        null=True,
        blank=True
    )

    antifungals = models.BooleanField(default=False, null=True)
    antifungals_drugs = JSONField(
        default=list,
        null=True,
        blank=True
    )

    documented_secondary_bacterial_infection = models.TextField(
        default="",
        null=True,
        verbose_name="any bacterial infection during treatment",
        blank=True
    )
    documented_fungal_infection = models.TextField(
        default="",
        null=True,
        verbose_name="any fungal infection during treatment",
        blank=True
    )
    newly_detected_comorbidities = models.TextField(
        default="",
        null=True,
        verbose_name="any new disease",
        blank=True
    )
    worsening_of_comorbidities = models.TextField(
        default="",
        null=True,
        verbose_name="is any disease worsened during treatment",
        blank=True
    )
    at_present_symptoms = ArrayField(
        models.CharField(default="", null=False, max_length=100),
        default=dict,
        null=True,
        blank=True
    )

    on_examination_vitals = JSONField(default=dict, null=True, blank=False)
    appearance_of_pallor = models.TextField(default=False, null=True)
    appearance_of_cyanosis = models.TextField(default=False, null=True)
    appearance_of_pedal_edema = models.TextField(default=False, null=True)
    appearance_of_pedal_edema_details = models.TextField(default="", null=True)

    systemic_examination = JSONField(
        default=dict,
        null=True,
        verbose_name="examinations of central nervous system"
    )

    single_breath_count = models.TextField(default="", null=True, blank=True)
    six_minute_walk_test = models.TextField(default="", null=True, blank=True)
    concurrent_medications = models.TextField(default="", null=True, blank=True)
    probable_diagnosis = models.TextField(default="", null=False, blank=False)
