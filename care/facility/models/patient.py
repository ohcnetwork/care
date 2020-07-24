import datetime
import enum

from django.db import models
from fernet_fields import EncryptedCharField, EncryptedIntegerField, EncryptedTextField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from care.facility.models import (
    DISEASE_CHOICES,
    BaseManager,
    District,
    FacilityBaseModel,
    LocalBody,
    PatientBaseModel,
    State,
    reverse_choices,
    pretty_boolean,
)
from care.facility.models.mixins.permissions.patient import PatientPermissionMixin
from care.facility.models.patient_base import (
    BLOOD_GROUP_CHOICES,
    DISEASE_STATUS_CHOICES,
    REVERSE_BLOOD_GROUP_CHOICES,
    REVERSE_DISEASE_STATUS_CHOICES,
)
from care.users.models import GENDER_CHOICES, REVERSE_GENDER_CHOICES, User, phone_number_regex
from care.utils.models.jsonfield import JSONField
from care.facility.models.mixins.permissions.facility import FacilityRelatedPermissionMixin


class PatientRegistration(PatientBaseModel, PatientPermissionMixin):
    # fields in the PatientSearch model
    PATIENT_SEARCH_KEYS = ["name", "gender", "phone_number", "date_of_birth", "year_of_birth", "state_id"]

    class SourceEnum(enum.Enum):
        CARE = 10
        COVID_TRACKER = 20
        STAY = 30

    SourceChoices = [(e.value, e.name) for e in SourceEnum]

    source = models.IntegerField(choices=SourceChoices, default=SourceEnum.CARE.value)
    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True)
    nearest_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, related_name="nearest_facility"
    )
    meta_info = models.OneToOneField("PatientMetaInfo", on_delete=models.SET_NULL, null=True)

    name = EncryptedCharField(max_length=200)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = EncryptedCharField(max_length=14, validators=[phone_number_regex])
    address = EncryptedTextField(default="")

    pincode = models.IntegerField(default=0, blank=False)

    date_of_birth = models.DateField(default=None, null=True)
    year_of_birth = models.IntegerField(default=0, null=True)

    nationality = models.CharField(max_length=255, default="", verbose_name="Nationality of Patient")
    passport_no = models.CharField(max_length=255, default="", verbose_name="Passport Number of Foreign Patients")
    # aadhar_no = models.CharField(max_length=255, default="", verbose_name="Aadhar Number of Patient")

    is_medical_worker = models.BooleanField(default=False, verbose_name="Is the Patient a Medical Worker")

    blood_group = models.CharField(
        choices=BLOOD_GROUP_CHOICES, null=True, blank=False, max_length=4, verbose_name="Blood Group of Patient"
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
    countries_travelled_old = models.TextField(
        null=True, blank=True, verbose_name="Countries Patient has Travelled to", editable=False
    )
    countries_travelled = JSONField(null=True, blank=True, verbose_name="Countries Patient has Travelled to")
    date_of_return = models.DateTimeField(
        blank=True, null=True, verbose_name="Return Date from the Last Country if Travelled"
    )

    allergies = models.TextField(default="", blank=True, verbose_name="Patient's Known Allergies")

    present_health = models.TextField(default="", blank=True, verbose_name="Patient's Current Health Details")
    ongoing_medication = models.TextField(default="", blank=True, verbose_name="Already pescribed medication if any")
    has_SARI = models.BooleanField(default=False, verbose_name="Does the Patient Suffer from SARI")

    is_antenatal = models.BooleanField(default=False, verbose_name="Does the patient require Prenatal Care ?")

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
    date_of_receipt_of_information = models.DateTimeField(
        null=True, blank=True, verbose_name="Patient's information received date"
    )

    allow_transfer = models.BooleanField(default=False)

    history = HistoricalRecords(excluded_fields=["patient_search_id", "meta_info"])

    objects = BaseManager()

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.age, self.get_gender_display())

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

        today = datetime.date.today()

        if (not self.age) and (self.date_of_birth):
            self.age = (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )

        self.date_of_receipt_of_information = (
            self.date_of_receipt_of_information
            if self.date_of_receipt_of_information is not None
            else datetime.datetime.now()
        )

        is_create = self.pk is None
        super().save(*args, **kwargs)
        if is_create or self.patient_search_id is None:
            ps = PatientSearch.objects.create(
                patient_external_id=self.external_id,
                name=self.name,
                gender=self.gender,
                phone_number=self.phone_number,
                date_of_birth=self.date_of_birth,
                year_of_birth=self.year_of_birth,
                state_id=self.state_id,
                patient_id=self.pk,
                facility=self.facility,
                allow_transfer=self.allow_transfer,
            )
            self.patient_search_id = ps.pk
            self.save()
        else:
            PatientSearch.objects.filter(pk=self.patient_search_id).update(
                patient_external_id=self.external_id,
                name=self.name,
                gender=self.gender,
                phone_number=self.phone_number,
                date_of_birth=self.date_of_birth,
                year_of_birth=self.year_of_birth,
                state_id=self.state_id,
                facility=self.facility,
                allow_transfer=self.allow_transfer,
                is_active=self.is_active,
            )

    CSV_MAPPING = {
        "external_id": "Patient ID",
        "facility__name": "Facility Name",
        "nearest_facility__name": "Nearest Facility",
        "date_of_birth": "Date Of Birth",
        "age": "Age",
        "gender": "Gender",
        "local_body__name": "Local Body",
        "district__name": "District",
        "state__name": "State",
        "nationality": "Nationality",
        "disease_status": "Disease Status",
        "number_of_aged_dependents": "Number of people aged above 60 living with the patient",
        "number_of_chronic_diseased_dependents": "Number of people who have chronic diseases living with the patient",
        "blood_group": "Blood Group",
        "is_medical_worker": "Is the Patient a Medical Worker",
        "contact_with_confirmed_carrier": "Confirmed Contact with a Covid19 Carrier",
        "contact_with_suspected_carrier": "Suspected Contact with a Covid19 Carrier",
        "estimated_contact_date": "Estimated Contact Date",
        "past_travel": "Travelled to Any Foreign Countries in the last 28 Days",
        "countries_travelled": "Countries Patient has Travelled to",
        "date_of_return": "Return Date from the Last Country if Travelled",
        "present_health": "Patient's Current Health Details",
        "ongoing_medication": "Already pescribed medication if any",
        "has_SARI": "Does the Patient Suffer from SARI",
        "date_of_receipt_of_information": "Patient's information received date",
    }

    CSV_MAKE_PRETTY = {
        "gender": (lambda x: REVERSE_GENDER_CHOICES[x]),
        "blood_group": (lambda x: REVERSE_BLOOD_GROUP_CHOICES[x]),
        "disease_status": (lambda x: REVERSE_DISEASE_STATUS_CHOICES[x]),
        "is_medical_worker": pretty_boolean,
    }


class PatientSearch(PatientBaseModel):
    patient_id = EncryptedIntegerField()

    name = models.CharField(max_length=120)
    gender = models.IntegerField(choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=14)
    date_of_birth = models.DateField(null=True)
    year_of_birth = models.IntegerField()
    state_id = models.IntegerField()

    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True)
    patient_external_id = EncryptedCharField(max_length=100, default="")

    allow_transfer = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

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


class PatientMetaInfo(models.Model):
    class OccupationEnum(enum.Enum):
        STUDENT = 1
        MEDICAL_WORKER = 2
        GOVT_EMPLOYEE = 3
        PRIVATE_EMPLOYEE = 4
        HOME_MAKER = 5
        WORKING_ABROAD = 6
        OTHERS = 7

    OccupationChoices = [(item.value, item.name) for item in OccupationEnum]

    occupation = models.IntegerField(choices=OccupationChoices)
    head_of_household = models.BooleanField()


class PatientContactDetails(models.Model):
    class RelationEnum(enum.IntEnum):
        FAMILY_MEMBER = 1
        FRIEND = 2
        RELATIVE = 3
        NEIGHBOUR = 4
        TRAVEL_TOGETHER = 5
        WHILE_AT_HOSPITAL = 6
        WHILE_AT_SHOP = 7
        WHILE_AT_OFFICE_OR_ESTABLISHMENT = 8
        WORSHIP_PLACE = 9
        OTHERS = 10

    class ModeOfContactEnum(enum.IntEnum):
        # "1. Touched body fluids of the patient (respiratory tract secretions/blood/vomit/saliva/urine/faces)"
        TOUCHED_BODY_FLUIDS = 1
        # "2. Had direct physical contact with the body of the patient
        # including physical examination without full precautions."
        DIRECT_PHYSICAL_CONTACT = 2
        # "3. Touched or cleaned the linens/clothes/or dishes of the patient"
        CLEANED_USED_ITEMS = 3
        # "4. Lives in the same household as the patient."
        LIVE_IN_SAME_HOUSEHOLD = 4
        # "5. Close contact within 3ft (1m) of the confirmed case without precautions."
        CLOSE_CONTACT_WITHOUT_PRECAUTION = 5
        # "6. Passenger of the aeroplane with a confirmed COVID -19 passenger for more than 6 hours."
        CO_PASSENGER_AEROPLANE = 6
        # "7. Health care workers and other contacts who had full PPE while handling the +ve case"
        HEALTH_CARE_WITH_PPE = 7
        # "8. Shared the same space(same class for school/worked in
        # same room/similar and not having a high risk exposure"
        SHARED_SAME_SPACE_WITHOUT_HIGH_EXPOSURE = 8
        # "9. Travel in the same environment (bus/train/Flight) but not having a high-risk exposure as cited above."
        TRAVELLED_TOGETHER_WITHOUT_HIGH_EXPOSURE = 9

    RelationChoices = [(item.value, item.name) for item in RelationEnum]
    ModeOfContactChoices = [(item.value, item.name) for item in ModeOfContactEnum]

    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT, related_name="contacted_patients")
    patient_in_contact = models.ForeignKey(
        PatientRegistration, on_delete=models.PROTECT, null=True, related_name="contacts"
    )
    relation_with_patient = models.IntegerField(choices=RelationChoices)
    mode_of_contact = models.IntegerField(choices=ModeOfContactChoices)
    date_of_first_contact = models.DateField(null=True)
    date_of_last_contact = models.DateField(null=True)

    is_primary = models.BooleanField(help_text="If false, then secondary contact")
    condition_of_contact_is_symptomatic = models.BooleanField(
        help_text="While in contact, did the patient showing symptoms"
    )

    deleted = models.BooleanField(default=False)

    objects = BaseManager()


class Disease(models.Model):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE, related_name="medical_history")
    disease = models.IntegerField(choices=DISEASE_CHOICES)
    details = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    objects = BaseManager()

    class Meta:
        indexes = [PartialIndex(fields=["patient", "disease"], unique=True, where=PQ(deleted=False))]


class FacilityPatientStatsHistory(FacilityBaseModel, FacilityRelatedPermissionMixin):
    facility = models.ForeignKey("Facility", on_delete=models.PROTECT)
    entry_date = models.DateField()
    num_patients_visited = models.IntegerField(default=0)
    num_patients_home_quarantine = models.IntegerField(default=0)
    num_patients_isolation = models.IntegerField(default=0)
    num_patient_referred = models.IntegerField(default=0)

    CSV_RELATED_MAPPING = {
        "facilitypatientstatshistory__entry_date": "Entry Date",
        "facilitypatientstatshistory__num_patients_visited": "Vistited Patients",
        "facilitypatientstatshistory__num_patients_home_quarantine": "Home Quarantined Patients",
        "facilitypatientstatshistory__num_patients_isolation": "Patients Isolated",
        "facilitypatientstatshistory__num_patient_referred": "Patients Reffered",
    }

    CSV_MAKE_PRETTY = {}

    class Meta:
        unique_together = (
            "facility",
            "entry_date",
        )
