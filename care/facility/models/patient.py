import datetime
import enum

from django.db import models
from fernet_fields import EncryptedCharField, EncryptedIntegerField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from care.facility.models import (
    DISEASE_CHOICES,
    BaseManager,
    BaseModel,
    DiseaseStatusEnum,
    District,
    FacilityBaseModel,
    LocalBody,
    PatientBaseModel,
    State,
    Ward,
    pretty_boolean,
)
from care.facility.models.mixins.permissions.facility import FacilityRelatedPermissionMixin
from care.facility.models.mixins.permissions.patient import PatientPermissionMixin
from care.facility.models.patient_base import (
    BLOOD_GROUP_CHOICES,
    DISEASE_STATUS_CHOICES,
    REVERSE_ADMIT_CHOICES,
    REVERSE_BLOOD_GROUP_CHOICES,
    REVERSE_DISEASE_STATUS_CHOICES,
    REVERSE_SYMPTOM_CATEGORY_CHOICES,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import GENDER_CHOICES, REVERSE_GENDER_CHOICES, User, phone_number_regex
from care.utils.models.jsonfield import JSONField


class PatientRegistration(PatientBaseModel, PatientPermissionMixin):
    # fields in the PatientSearch model
    PATIENT_SEARCH_KEYS = [
        "name",
        "gender",
        "phone_number",
        "date_of_birth",
        "year_of_birth",
        "state_id",
    ]

    class SourceEnum(enum.Enum):
        CARE = 10
        COVID_TRACKER = 20
        STAY = 30

    SourceChoices = [(e.value, e.name) for e in SourceEnum]

    class ActionEnum(enum.Enum):
        PENDING = 10
        SPECIALIST_REQUIRED = 30
        PLAN_FOR_HOME_CARE = 40
        FOLLOW_UP_NOT_REQUIRED = 50
        COMPLETE = 60
        REVIEW = 70
        NOT_REACHABLE = 80

    ActionChoices = [(e.value, e.name) for e in ActionEnum]

    class TestTypeEnum(enum.Enum):
        UNK = 10
        ANTIGEN = 20
        RTPCR = 30
        CBNAAT = 40
        TRUENAT = 50

    TestTypeChoices = [(e.value, e.name) for e in TestTypeEnum]

    source = models.IntegerField(choices=SourceChoices, default=SourceEnum.CARE.value)
    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True)
    nearest_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, related_name="nearest_facility",
    )
    meta_info = models.OneToOneField("PatientMetaInfo", on_delete=models.SET_NULL, null=True)

    # name_old = EncryptedCharField(max_length=200, default="")
    name = models.CharField(max_length=200, default="")

    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)

    # phone_number_old = EncryptedCharField(max_length=14, validators=[phone_number_regex], default="")
    phone_number = models.CharField(max_length=14, validators=[phone_number_regex], default="")

    emergency_phone_number = models.CharField(max_length=14, validators=[phone_number_regex], default="")

    # address_old = EncryptedTextField(default="")
    address = models.TextField(default="")

    pincode = models.IntegerField(default=0, blank=True, null=True)

    date_of_birth = models.DateField(default=None, null=True)
    year_of_birth = models.IntegerField(default=0, null=True)

    nationality = models.CharField(max_length=255, default="", verbose_name="Nationality of Patient")
    passport_no = models.CharField(max_length=255, default="", verbose_name="Passport Number of Foreign Patients")
    # aadhar_no = models.CharField(max_length=255, default="", verbose_name="Aadhar Number of Patient")

    is_medical_worker = models.BooleanField(default=False, verbose_name="Is the Patient a Medical Worker")

    blood_group = models.CharField(
        choices=BLOOD_GROUP_CHOICES, null=True, blank=False, max_length=4, verbose_name="Blood Group of Patient",
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
        null=True, blank=True, verbose_name="Countries Patient has Travelled to", editable=False,
    )
    countries_travelled = JSONField(null=True, blank=True, verbose_name="Countries Patient has Travelled to")
    date_of_return = models.DateTimeField(
        blank=True, null=True, verbose_name="Return Date from the Last Country if Travelled",
    )

    allergies = models.TextField(default="", blank=True, verbose_name="Patient's Known Allergies")

    present_health = models.TextField(default="", blank=True, verbose_name="Patient's Current Health Details")
    ongoing_medication = models.TextField(default="", blank=True, verbose_name="Already pescribed medication if any")
    has_SARI = models.BooleanField(default=False, verbose_name="Does the Patient Suffer from SARI")

    is_antenatal = models.BooleanField(default=False, verbose_name="Does the patient require Prenatal Care ?")

    ward_old = models.CharField(max_length=255, default="", verbose_name="Ward of Patient", blank=False)

    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)
    local_body = models.ForeignKey(LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    is_migrant_worker = models.BooleanField(default=False, verbose_name="Is Patient a Migrant Worker",)

    disease_status = models.IntegerField(
        choices=DISEASE_STATUS_CHOICES, default=1, blank=True, verbose_name="Disease Status",
    )

    number_of_aged_dependents = models.IntegerField(
        default=0, verbose_name="Number of people aged above 60 living with the patient", blank=True,
    )
    number_of_chronic_diseased_dependents = models.IntegerField(
        default=0, verbose_name="Number of people who have chronic diseases living with the patient", blank=True,
    )

    last_edited = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="patient_last_edited_by",)

    action = models.IntegerField(choices=ActionChoices, default=ActionEnum.PENDING.value)
    review_time = models.DateTimeField(null=True, blank=True, verbose_name="Patient's next review time")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="patient_created_by")
    is_active = models.BooleanField(
        default=True, help_text="Not active when discharged, or removed from the watchlist",
    )

    patient_search_id = EncryptedIntegerField(help_text="FKey to PatientSearch", null=True)
    date_of_receipt_of_information = models.DateTimeField(
        null=True, blank=True, verbose_name="Patient's information received date"
    )

    test_id = models.CharField(default="", max_length=100, null=True, blank=True)

    # Issue #600 Care_Fe
    date_of_test = models.DateTimeField(null=True, blank=True, verbose_name="Patient's test Date")
    srf_id = models.CharField(max_length=200, blank=True, default="")
    test_type = models.IntegerField(choices=TestTypeChoices, default=TestTypeEnum.UNK.value)

    allow_transfer = models.BooleanField(default=False)

    last_consultation = models.ForeignKey(PatientConsultation, on_delete=models.SET_NULL, null=True, default=None)

    will_donate_blood = models.BooleanField(default=None, null=True, verbose_name="Is Patient Willing to donate Blood",)

    fit_for_blood_donation = models.BooleanField(
        default=None, null=True, verbose_name="Is Patient fit for donating Blood",
    )

    # IDSP REQUIREMENTS
    village = models.CharField(
        max_length=255, default=None, verbose_name="Vilalge Name of Patient (IDSP Req)", null=True, blank=True,
    )
    designation_of_health_care_worker = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Designation of Health Care Worker (IDSP Req)",
        null=True,
        blank=True,
    )
    instituion_of_health_care_worker = models.CharField(
        max_length=255, default=None, verbose_name="Institution of Healtcare Worker (IDSP Req)", null=True, blank=True,
    )
    transit_details = models.CharField(
        max_length=255, default=None, verbose_name="Transit Details (IDSP Req)", null=True, blank=True,
    )
    frontline_worker = models.CharField(
        max_length=255, default=None, verbose_name="Front Line Worker (IDSP Req)", null=True, blank=True,
    )
    date_of_result = models.DateTimeField(null=True, blank=True, default=None, verbose_name="Patient's result Date")
    number_of_primary_contacts = models.IntegerField(
        null=True, default=None, blank=True, verbose_name="Number of Primary Contacts"
    )
    number_of_secondary_contacts = models.IntegerField(
        null=True, default=None, blank=True, verbose_name="Number of Secondary Contacts"
    )
    # IDSP Requirements End

    # Vaccination Fields

    is_vaccinated = models.BooleanField(default=False, verbose_name="Is the Patient Vaccinated Against COVID-19")
    covin_id = models.CharField(
        max_length=15, default=None, null=True, blank=True, verbose_name="COVID-19 Vaccination ID",
    )

    # Extras
    cluster_name = models.CharField(
        max_length=255, default=None, verbose_name="Name/ Cluster of Contact", null=True, blank=True,
    )
    is_declared_positive = models.BooleanField(default=None, null=True, verbose_name="Is Patient Declared Positive",)
    date_declared_positive = models.DateTimeField(
        null=True, blank=True, verbose_name="Date Patient is Declared Positive"
    )

    history = HistoricalRecords(excluded_fields=["patient_search_id", "meta_info"])

    objects = BaseManager()

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.age, self.get_gender_display())

    @property
    def tele_consultation_history(self):
        return self.patientteleconsultation_set.order_by("-id")

    def _alias_recovery_to_recovered(self) -> None:
        if self.disease_status == DiseaseStatusEnum.RECOVERY.value:
            self.disease_status = DiseaseStatusEnum.RECOVERED.value

    def save(self, *args, **kwargs) -> None:
        """
        While saving, if the local body is not null, then district will be local body's district
        Overriding save will help in a collision where the local body's district and district fields are different.

        It also aliases the DiseaseStatus RECOVERED to RECOVERY
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

        if self.date_of_birth:
            self.age = (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        elif self.year_of_birth:
            self.age = today.year - self.year_of_birth

        self.date_of_receipt_of_information = (
            self.date_of_receipt_of_information
            if self.date_of_receipt_of_information is not None
            else datetime.datetime.now()
        )

        is_create = self.pk is None
        self._alias_recovery_to_recovered()
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
        "name": "Patient Name",
        "phone_number": "Patient Phone Number",
        "date_of_birth": "Date of Birth",
        # "year_of_birth": "Year of Birth",
        "facility__name": "Facility Name",
        # "nearest_facility__name": "Nearest Facility",
        "age": "Age",
        "gender": "Gender",
        "ward__name": "Ward Name",
        "ward__number": "Ward Number",
        "local_body__name": "Local Body",
        "district__name": "District",
        "state__name": "State",
        "address": "Address",
        "nationality": "Nationality",
        "disease_status": "Disease Status",
        # "state_test_id": "State Test ID",
        "last_consultation__admitted": "Admission Status",
        "last_consultation__admitted_to": "Admission Room Type",
        # Reffered or transferred
        # remarks
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
        "is_migrant_worker": "Is the Patient a Migrant Worker",
        "present_health": "Patient's Current Health Details",
        "ongoing_medication": "Already pescribed medication if any",
        "has_SARI": "Does the Patient Suffer from SARI",
        "date_of_receipt_of_information": "Patient's information received date",
        "will_donate_blood": "Will Patient Donate Blood?",
        "fit_for_blood_donation": "Is Patient Fit for Blood Donation?",
        "date_of_test": "Date of Sample Test",
        "srf_id": "SRF Test Id",
        # IDSP Data
        "village": "Village",
        "designation_of_health_care_worker": "Designation of Health Care Worker",
        "instituion_of_health_care_worker": "Institution of Health Care Worker",
        "transit_details": "Transit Details",
        "frontline_worker": "FrontLine Worker",
        "date_of_result": "Date of Result",
        "number_of_primary_contacts": "Number of Primary Contacts",
        "number_of_secondary_contacts": "Number of Secondary Contacts",
        "cluster_name": "Name/ Cluster of Contact",
        "is_declared_positive": "Is Patient Declared Positive",
        "date_declared_positive": "Date Patient is Declared Positive",
        # Consultation Data
        "last_consultation__admission_date": "Date of Admission",
        "last_consultation__symptoms_onset_date": "Date of Onset of Symptoms",
        "last_consultation__symptoms": "Symptoms at time of consultation",
        "last_consultation__category": "Category",
        "last_consultation__examination_details": "Examination Details",
        "last_consultation__suggestion": "Suggestion",
        "last_consultation__created_date": "Date of Consultation",
        "last_consultation__discharge_date": "Date of Discharge",
    }

    CSV_MAKE_PRETTY = {
        "gender": (lambda x: REVERSE_GENDER_CHOICES[x]),
        "blood_group": (lambda x: REVERSE_BLOOD_GROUP_CHOICES[x]),
        "disease_status": (lambda x: REVERSE_DISEASE_STATUS_CHOICES[x]),
        "is_medical_worker": pretty_boolean,
        "will_donate_blood": pretty_boolean,
        "fit_for_blood_donation": pretty_boolean,
        "is_migrant_worker": pretty_boolean,
        "is_declared_positive": pretty_boolean,
        # Consultation Data
        "last_consultation__category": (lambda x: REVERSE_SYMPTOM_CATEGORY_CHOICES.get(x, "-")),
        "last_consultation__suggestion": (lambda x: PatientConsultation.REVERSE_SUGGESTION_CHOICES.get(x, "-")),
        "last_consultation__admitted": pretty_boolean,
        "last_consultation__admitted_to": (lambda x: REVERSE_ADMIT_CHOICES.get(x, "-")),
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
        PatientRegistration, on_delete=models.PROTECT, null=True, related_name="contacts",
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
    num_patient_confirmed_positive = models.IntegerField(default=0)

    CSV_RELATED_MAPPING = {
        "facilitypatientstatshistory__entry_date": "Entry Date",
        "facilitypatientstatshistory__num_patients_visited": "Vistited Patients",
        "facilitypatientstatshistory__num_patients_home_quarantine": "Home Quarantined Patients",
        "facilitypatientstatshistory__num_patients_isolation": "Patients Isolated",
        "facilitypatientstatshistory__num_patient_referred": "Patients Reffered",
        "facilitypatientstatshistory__num_patient_confirmed_positive": "Patients Confirmed Positive",
    }

    CSV_MAKE_PRETTY = {}

    class Meta:
        unique_together = (
            "facility",
            "entry_date",
        )


class PatientMobileOTP(BaseModel):
    is_used = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=14, validators=[phone_number_regex])
    otp = models.CharField(max_length=10)
