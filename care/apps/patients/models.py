from django.db import models
from apps.accounts.models import District, State, LocalBody
from apps.commons.models import ActiveObjectsManager
from apps.facility.models import Facility, TestingLab
from apps.accounts.models import User
from apps.commons.constants import GENDER_CHOICES
from apps.commons.models import SoftDeleteTimeStampedModel
from apps.commons.validators import phone_number_regex
from fernet_fields import EncryptedCharField, EncryptedIntegerField, EncryptedTextField
from partial_index import PQ, PartialIndex
from apps.patients import constants
from simple_history.models import HistoricalRecords
from libs.jsonfield import JSONField


class Patient(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient
    """
    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    ]
    DISEASE_STATUS_CHOICES = [
        (constants.DISEASE_STATUS_CHOICES.SU, "SUSPECTED"),
        (constants.DISEASE_STATUS_CHOICES.PO, "POSITIVE"),
        (constants.DISEASE_STATUS_CHOICES.NE, "NEGATIVE"),
        (constants.DISEASE_STATUS_CHOICES.RE, "RECOVERY"),
        (constants.DISEASE_STATUS_CHOICES.RD, "RECOVERED"),
        (constants.DISEASE_STATUS_CHOICES.EX, "EXPIRED"),
    ]
    SOURCE_CHOICES = [
        (constants.SOURCE_CHOICES.CA, "CARE"),
        (constants.SOURCE_CHOICES.CT, "COVID_TRACKER"),
        (constants.SOURCE_CHOICES.ST, "STAY"),
    ]
    source = models.IntegerField(
        choices=SOURCE_CHOICES, default=constants.SOURCE_CHOICES.CA
    )
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True)
    nearest_facility = models.ForeignKey(
        Facility, on_delete=models.SET_NULL, null=True, related_name="nearest_facility"
    )
    icmr_id = models.CharField(max_length=15, blank=True)
    govt_id = models.CharField(max_length=15, blank=True)
    name = EncryptedCharField(max_length=200)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = EncryptedCharField(max_length=14, validators=[phone_number_regex])
    address = EncryptedTextField(default="")
    date_of_birth = models.DateField(default=None, null=True)
    year_of_birth = models.IntegerField(default=0, null=True)
    nationality = models.CharField(
        max_length=255, default="", verbose_name="Nationality of Patient"
    )
    passport_no = models.CharField(
        max_length=255, default="", verbose_name="Passport Number of Foreign Patients"
    )
    aadhar_no = models.CharField(
        max_length=255, default="", verbose_name="Aadhar Number of Patient"
    )
    is_medical_worker = models.BooleanField(
        default=False, verbose_name="Is the Patient a Medical Worker"
    )
    blood_group = models.CharField(
        choices=BLOOD_GROUP_CHOICES,
        null=True,
        blank=True,
        max_length=4,
        verbose_name="Blood Group of Patient",
    )
    contact_with_confirmed_carrier = models.BooleanField(
        default=False, verbose_name="Confirmed Contact with a Covid19 Carrier"
    )
    contact_with_suspected_carrier = models.BooleanField(
        default=False, verbose_name="Suspected Contact with a Covid19 Carrier"
    )
    estimated_contact_date = models.DateTimeField(null=True, blank=True)
    past_travel = models.BooleanField(
        default=False,
        verbose_name="Travelled to Any Foreign Countries in the last 28 Days",
    )
    countries_travelled_old = models.TextField(
        null=True,
        blank=True,
        verbose_name="Countries Patient has Travelled to",
        editable=False,
    )
    countries_travelled = JSONField(
        null=True, blank=True, verbose_name="Countries Patient has Travelled to"
    )
    date_of_return = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Return Date from the Last Country if Travelled",
    )
    present_health = models.TextField(
        default="", blank=True, verbose_name="Patient's Current Health Details"
    )
    ongoing_medication = models.TextField(
        default="", blank=True, verbose_name="Already pescribed medication if any"
    )
    has_SARI = models.BooleanField(
        default=False, verbose_name="Does the Patient Suffer from SARI"
    )
    local_body = models.ForeignKey(
        LocalBody, on_delete=models.SET_NULL, null=True, blank=True
    )
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True
    )
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    disease_status = models.IntegerField(
        choices=DISEASE_STATUS_CHOICES,
        default=constants.DISEASE_STATUS_CHOICES.SU,
        blank=True,
        verbose_name="Disease Status",
    )
    number_of_aged_dependents = models.IntegerField(
        default=0,
        verbose_name="Number of people aged above 60 living with the patient",
        blank=True,
    )
    number_of_chronic_diseased_dependents = models.IntegerField(
        default=0,
        verbose_name="Number of people who have chronic diseases living with the patient",
        blank=True,
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Not active when discharged, or removed from the watchlist",
    )
    patient_search_id = EncryptedIntegerField(
        help_text="FKey to PatientSearch", null=True
    )
    date_of_receipt_of_information = models.DateTimeField(
        null=True, blank=True, verbose_name="Patient's information received date"
    )
    symptoms = models.ManyToManyField('CovidSymptom', through='PatientSymptom')
    diseases = models.ManyToManyField('Disease' , through='PatientDisease')

    objects = ActiveObjectsManager()


class PatientDisease(SoftDeleteTimeStampedModel):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    disease = models.ForeignKey('Disease', on_delete=models.CASCADE)


class PatientSymptom(SoftDeleteTimeStampedModel):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    symptom = models.ForeignKey('CovidSymptom', on_delete=models.CASCADE)


class CovidSymptom(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class Disease(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class PatientFacility(SoftDeleteTimeStampedModel):
    """
    model to represent patient facility
    """

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    patient_facility_id = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.patient.name}<>{self.facility.name}"

    class Meta:
        unique_together = ('facility', 'patient_facility_id')
