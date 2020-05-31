import datetime
from django.db import models
from apps.accounts import models as accounts_models
from apps.commons import (
    models as commons_models,
    constants as commons_constants,
    validators as commons_validators,
)
from apps.facility.models import Facility, TestingLab
from fernet_fields import EncryptedCharField, EncryptedIntegerField, EncryptedTextField
from partial_index import PQ, PartialIndex
from apps.patients import constants
from simple_history.models import HistoricalRecords
from libs.jsonfield import JSONField


class PatientGroup(commons_models.SoftDeleteTimeStampedModel):
    """
    model to represent patient Group
    """

    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"], help_text="Name of the patient group",
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}<>{self.description}"


class Patient(commons_models.SoftDeleteTimeStampedModel, commons_models.AddressModel):
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
    SOURCE_CHOICES = [
        (constants.SOURCE_CHOICES.CA, "CARE"),
        (constants.SOURCE_CHOICES.CT, "COVID_TRACKER"),
        (constants.SOURCE_CHOICES.ST, "STAY"),
    ]

    source = models.IntegerField(choices=SOURCE_CHOICES, default=constants.SOURCE_CHOICES.CA)
    nearest_facility = models.ForeignKey(
        Facility, on_delete=models.SET_NULL, null=True, related_name="nearest_facility"
    )
    icmr_id = models.CharField(max_length=15, blank=True, null=True, unique=True)
    govt_id = models.CharField(max_length=15, blank=True, null=True, unique=True)
    name = models.CharField(max_length=200)
    month = models.PositiveIntegerField(null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    gender = models.IntegerField(choices=commons_constants.GENDER_CHOICES, blank=False)
    phone_number = models.CharField(max_length=14, validators=[commons_validators.phone_number_regex])
    phone_number_belongs_to = models.PositiveSmallIntegerField(default=1)
    date_of_birth = models.DateField(default=None, null=True)
    nationality = models.CharField(max_length=255, verbose_name="Nationality of Patient", default="indian")
    passport_no = models.CharField(
        max_length=255, verbose_name="Passport Number of Foreign Patients", unique=True, null=True, blank=True,
    )
    aadhar_no = models.CharField(
        max_length=255, verbose_name="Aadhar Number of Patient", unique=True, null=True, blank=True,
    )
    is_medical_worker = models.BooleanField(default=False, verbose_name="Is the Patient a Medical Worker")
    blood_group = models.CharField(choices=BLOOD_GROUP_CHOICES, max_length=4, verbose_name="Blood Group of Patient",)
    contact_with_confirmed_carrier = models.BooleanField(
        default=False, verbose_name="Confirmed Contact with a Covid19 Carrier"
    )
    contact_with_suspected_carrier = models.BooleanField(
        default=False, verbose_name="Suspected Contact with a Covid19 Carrier"
    )
    estimated_contact_date = models.DateTimeField(null=True, blank=True)
    past_travel = models.BooleanField(
        default=False, verbose_name="Travelled to Any Foreign Countries in the last 28 Days",
    )
    countries_travelled_old = models.TextField(
        null=True, blank=True, verbose_name="Countries Patient has Travelled to", editable=False,
    )
    countries_travelled = JSONField(null=True, blank=True, verbose_name="Countries Patient has Travelled to")
    date_of_return = models.DateTimeField(
        blank=True, null=True, verbose_name="Return Date from the Last Country if Travelled",
    )
    present_health = models.TextField(default="", blank=True, verbose_name="Patient's Current Health Details")
    ongoing_medication = models.TextField(default="", blank=True, verbose_name="Already pescribed medication if any")
    has_SARI = models.BooleanField(default=False, verbose_name="Does the Patient Suffer from SARI")
    local_body = models.ForeignKey(accounts_models.LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    number_of_aged_dependents = models.IntegerField(
        default=0, verbose_name="Number of people aged above 60 living with the patient", blank=True,
    )
    number_of_chronic_diseased_dependents = models.IntegerField(
        default=0, verbose_name="Number of people who have chronic diseases living with the patient", blank=True,
    )
    created_by = models.ForeignKey(accounts_models.User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(
        default=True, help_text="Not active when discharged, or removed from the watchlist",
    )
    date_of_receipt_of_information = models.DateTimeField(
        null=True, blank=True, verbose_name="Patient's information received date"
    )
    cluster_group = models.ForeignKey(
        PatientGroup, on_delete=models.PROTECT, related_name="patients", null=True, blank=True,
    )
    clinical_status_updated_at = models.DateTimeField(null=True, blank=True)
    portea_called_at = models.DateTimeField(null=True, blank=True)
    portea_able_to_connect = models.BooleanField(null=True, blank=True, verbose_name="Is the portea able to connect")
    symptoms = models.ManyToManyField("CovidSymptom", through="PatientSymptom")
    diseases = models.ManyToManyField("Disease", through="PatientDisease")
    covid_status = models.ForeignKey(
        "CovidStatus", null=True, blank=True, on_delete=models.CASCADE, related_name="covid_status",
    )
    clinical_status = models.ForeignKey(
        "ClinicalStatus", null=True, blank=True, on_delete=models.CASCADE, related_name="clinical_status",
    )
    current_facility = models.ForeignKey(
        "PatientFacility", null=True, blank=True, on_delete=models.CASCADE, related_name="current_facility",
    )
    patient_status = models.CharField(max_length=25, choices=constants.PATIENT_STATUS_CHOICES, blank=True)
    history = HistoricalRecords()

    objects = commons_models.ActiveObjectsManager()

    class Meta:
        unique_together = (
            "aadhar_no",
            "passport_no",
            "cluster_group",
        )

    def __str__(self):
        return "{} - {}".format(self.name, self.get_gender_display())


class PatientDisease(commons_models.SoftDeleteTimeStampedModel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE)
    disease = models.ForeignKey("Disease", on_delete=models.CASCADE)


class PatientSymptom(commons_models.SoftDeleteTimeStampedModel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE)
    symptom = models.ForeignKey("CovidSymptom", on_delete=models.CASCADE)


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


class PatientStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class CovidStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class ClinicalStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}"


class PatientFacility(commons_models.SoftDeleteTimeStampedModel):
    """
    model to represent patient facility
    """

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    patient_facility_id = models.CharField(max_length=15)
    patient_status = models.ForeignKey("PatientStatus", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.facility.name}"

    class Meta:
        unique_together = ("facility", "patient_facility_id")


class PatientTimeLine(models.Model):
    """
    Model to store timelines of a patient
    """

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    date = models.DateField(default=datetime.date.today)
    description = models.TextField()

    def __str__(self):
        return f"{self.patient.name} - {self.date}"


class PatientFamily(commons_models.SoftDeleteTimeStampedModel, commons_models.AddressModel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE)
    name = models.CharField(max_length=55)
    relation = models.CharField(max_length=55)
    age_month = models.PositiveIntegerField()
    age_year = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=15)
    gender = models.IntegerField(choices=commons_constants.GENDER_CHOICES, blank=False)

    def __str__(self):
        return f"{self.patient.name} {self.relation}'s {self.name}"


class PortieCallingDetail(commons_models.SoftDeleteTimeStampedModel):

    portie = models.ForeignKey(accounts_models.User, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    patient_family = models.ForeignKey(PatientFamily, on_delete=models.CASCADE, null=True, blank=True)
    called_at = models.DateTimeField()
    able_to_connect = models.BooleanField(default=True)
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"{self.portie.name} called {self.patient.name} at {self.called_at}"


class PatientSampleTest(commons_models.SoftDeleteTimeStampedModel):
    """
    model for the patient sample test
    """

    SAMPLE_TEST_RESULT_CHOICES = [
        (constants.SAMPLE_TEST_RESULT_MAP.SS, "SAMPLE SENT"),
        (constants.SAMPLE_TEST_RESULT_MAP.PO, "POSITIVE"),
        (constants.SAMPLE_TEST_RESULT_MAP.NG, "NEGATIVE"),
        (constants.SAMPLE_TEST_RESULT_MAP.PP, "PRESUMPTIVE POSITIVE"),
        (constants.SAMPLE_TEST_RESULT_MAP.AW, "AWAITING"),
        (constants.SAMPLE_TEST_RESULT_MAP.TI, "TEST INCONCLUSIVE"),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="patients")
    testing_lab = models.ForeignKey(TestingLab, on_delete=models.PROTECT, related_name="labs")
    doctor_name = models.CharField(max_length=255, null=True, blank=True)
    result = models.IntegerField(choices=SAMPLE_TEST_RESULT_CHOICES, default=constants.SAMPLE_TEST_RESULT_MAP.SS)
    date_of_sample = models.DateTimeField(auto_now_add=True, verbose_name="date at which sample tested")
    date_of_result = models.DateTimeField(null=True, blank=True, verbose_name="date of result of sample")
    status_updated_at = models.DateTimeField(auto_now=True, verbose_name="date at which sample updated")

    def __str__(self):
        return f"{self.patient.name} at {self.date_of_sample}"


class PatientTransfer(commons_models.SoftDeleteTimeStampedModel):
    """
    Model to store details about the transfer of patient from one facility to another
    """

    from_patient_facility = models.ForeignKey(
        PatientFacility, on_delete=models.CASCADE, help_text="Current patient facility of a patient",
    )
    to_facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, help_text="New Facility in which the patient can be transferred",
    )
    status = models.PositiveSmallIntegerField(
        choices=constants.TRANSFER_STATUS_CHOICES, default=constants.TRANSFER_STATUS.PENDING,
    )
    status_updated_at = models.DateTimeField(
        null=True, blank=True, help_text="Date and time at wihich the status is updated"
    )
    comments = models.TextField(null=True, blank=True, help_text="comments related to patient transfer request")

    def __str__(self):
        return f"""
            Patient: {self.from_patient_facility.patient.name} - From: {self.from_patient_facility.facility.name} 
            - To: {self.to_facility.name}
        """
