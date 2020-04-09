import datetime

from django.db import models
from fernet_fields import EncryptedCharField, EncryptedIntegerField, EncryptedTextField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from care.facility.models import (
    DISEASE_CHOICES,
    District,
    FacilityBaseModel,
    LocalBody,
    PatientBaseModel,
    SoftDeleteManager,
    State,
)
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES, DISEASE_STATUS_CHOICES
from care.users.models import GENDER_CHOICES, User, phone_number_regex


class PatientRegistration(PatientBaseModel):
    # fields in the PatientSearch model
    PATIENT_SEARCH_KEYS = ["name", "gender", "phone_number", "date_of_birth", "year_of_birth", "state_id"]

    def __init__(self, *args, **kwargs):
        super(PatientRegistration, self).__init__(*args, **kwargs)
        self._diff = {}

    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True)

    name = EncryptedCharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = EncryptedCharField(max_length=14, validators=[phone_number_regex])
    address = EncryptedTextField(default="")

    date_of_birth = models.DateField(default=None, null=True)
    year_of_birth = models.IntegerField(default=0, null=True)

    nationality = models.CharField(max_length=255, default="", verbose_name="Nationality of Patient")
    passport_no = models.CharField(max_length=255, default="", verbose_name="Passport Number of Foreign Patients")
    aadhar_no = models.CharField(max_length=255, default="", verbose_name="Aadhar Number of Patient")

    is_medical_worker = models.BooleanField(default=False, verbose_name="Is the Patient a Medical Worker")

    blood_group = models.CharField(
        choices=BLOOD_GROUP_CHOICES, null=True, blank=True, max_length=4, verbose_name="Blood Group of Patient"
    )

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
    countries_travelled = models.TextField(default="", blank=True, verbose_name="Countries Patient has Travelled to")
    date_of_return = models.DateTimeField(
        blank=True, null=True, verbose_name="Return Date from the Last Country if Travelled"
    )

    present_health = models.TextField(default="", blank=True, verbose_name="Patient's Current Health Details")
    ongoing_medication = models.TextField(default="", blank=True, verbose_name="Already pescribed medication if any")
    has_SARI = models.BooleanField(default=False, verbose_name="Does the Patient Suffer from SARI")

    local_body = models.ForeignKey(LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    disease_status = models.IntegerField(
        choices=DISEASE_STATUS_CHOICES, default=1, blank=True, verbose_name="Disease Status"
    )

    number_of_aged_dependents = models.IntegerField(
        default=0, verbose_name="Number of people aged above 60 living with the patient", blank=True
    )
    number_of_chronic_diseased_dependents = models.IntegerField(
        default=0, verbose_name="Number of people who have chronic diseases living with the patient", blank=True
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(
        default=True, help_text="Not active when discharged, or removed from the watchlist",
    )

    patient_search_id = EncryptedIntegerField(help_text="FKey to PatientSearch", null=True)

    history = HistoricalRecords(excluded_fields=["patient_search_id"])

    objects = SoftDeleteManager()

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.age, self.get_gender_display())

    @staticmethod
    def has_write_permission(request):
        return request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or request.user == self.created_by
            or (self.facility and request.user == self.facility.created_by)
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district == self.district
            )
        )

    def has_object_destroy_permission(self, request):
        """Currently refers only to delete action"""
        return request.user.is_superuser

    def has_object_update_permission(self, request):
        return (
            request.user.is_superuser
            or request.user == self.created_by
            or (self.facility and request.user == self.facility.created_by)
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district == self.district
            )
            #  TODO State Level Permissions
        )

    @property
    def tele_consultation_history(self):
        return self.patientteleconsultation_set.order_by("-id")

    def save(self, *args, **kwargs) -> None:
        """
        While saving, if the local body is not null, then district will be local body's district
        Overriding save will help in a collision where the local body's district and district fields are different.

        It also creates/updates the PatientSearch model

        Parameters
        ----------
        args: list of args - not used
        kwargs: keyword args - not used

        Returns
        -------
        None
        """
        if self.local_body is not None:
            self.district = self.local_body.district
        if self.district is not None:
            self.state = self.district.state

        self.year_of_birth = (
            self.date_of_birth.year if self.date_of_birth is not None else datetime.datetime.now().year - self.age
        )

        is_create = self.pk is None
        super().save(*args, **kwargs)
        if is_create or self.patient_search_id is None:
            ps = PatientSearch.objects.create(
                name=self.name,
                gender=self.gender,
                phone_number=self.phone_number,
                date_of_birth=self.date_of_birth,
                year_of_birth=self.year_of_birth,
                state_id=self.state_id,
                patient_id=self.pk,
            )
            self.patient_search_id = ps.pk
            self.save()
        else:
            PatientSearch.objects.filter(pk=self.patient_search_id).update(
                name=self.name,
                gender=self.gender,
                phone_number=self.phone_number,
                date_of_birth=self.date_of_birth,
                year_of_birth=self.year_of_birth,
                state_id=self.state_id,
            )


class PatientSearch(models.Model):
    patient_id = EncryptedIntegerField()

    name = models.CharField(max_length=120)
    gender = models.IntegerField(choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=14)
    date_of_birth = models.DateField(null=True)
    year_of_birth = models.IntegerField()
    state_id = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["year_of_birth", "date_of_birth", "phone_number"]),
            models.Index(fields=["year_of_birth", "phone_number"]),
        ]

    @staticmethod
    def has_read_permission(request):
        if request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return True
        elif request.user.user_type >= User.TYPE_VALUE_MAP["Staff"] and request.user.verified:
            return True
        return False


class Disease(models.Model):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE, related_name="medical_history")
    disease = models.IntegerField(choices=DISEASE_CHOICES)
    details = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [PartialIndex(fields=["patient", "disease"], unique=True, where=PQ(deleted=False))]


class FacilityPatientStatsHistory(FacilityBaseModel):
    facility = models.ForeignKey("Facility", on_delete=models.PROTECT)
    entry_date = models.DateField()
    num_patients_visited = models.IntegerField(default=0)
    num_patients_home_quarantine = models.IntegerField(default=0)
    num_patients_isolation = models.IntegerField(default=0)
    num_patient_referred = models.IntegerField(default=0)

    class Meta:
        unique_together = (
            "facility",
            "entry_date",
        )
