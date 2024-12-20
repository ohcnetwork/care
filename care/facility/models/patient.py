import enum
from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Case, F, Func, JSONField, Value, When
from django.db.models.functions import Coalesce, Now
from django.template.defaultfilters import pluralize
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from care.facility.models import (
    DISEASE_CHOICES,
    DiseaseStatusEnum,
    District,
    Facility,
    FacilityBaseModel,
    LocalBody,
    PatientBaseModel,
    State,
    Ward,
)
from care.facility.models.icd11_diagnosis import ConditionVerificationStatus
from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
    PatientPermissionMixin,
)
from care.facility.models.patient_base import (
    BLOOD_GROUP_CHOICES,
    DISEASE_STATUS_CHOICES,
    REVERSE_CATEGORY_CHOICES,
    REVERSE_NEW_DISCHARGE_REASON_CHOICES,
    REVERSE_ROUTE_TO_FACILITY_CHOICES,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.static_data.icd11 import get_icd11_diagnoses_objects_by_ids
from care.users.models import GENDER_CHOICES, REVERSE_GENDER_CHOICES, User
from care.utils.models.base import BaseManager, BaseModel
from care.utils.models.validators import mobile_or_landline_number_validator


class RationCardCategory(models.TextChoices):
    NON_CARD_HOLDER = "NO_CARD", _("Non-card holder")
    BPL = "BPL", _("BPL")
    APL = "APL", _("APL")


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

    class VaccineEnum(enum.Enum):
        COVISHIELD = "CoviShield"
        COVAXIN = "Covaxin"
        SPUTNIK = "Sputnik"
        MODERNA = "Moderna"
        PFIZER = "Pfizer"
        JANSSEN = "Janssen"
        SINOVAC = "Sinovac"

    VaccineChoices = [(e.value, e.name) for e in VaccineEnum]

    class ActionEnum(enum.Enum):
        NO_ACTION = 10
        PENDING = 20
        SPECIALIST_REQUIRED = 30
        PLAN_FOR_HOME_CARE = 40
        FOLLOW_UP_NOT_REQUIRED = 50
        COMPLETE = 60
        REVIEW = 70
        NOT_REACHABLE = 80
        DISCHARGE_RECOMMENDED = 90

    ActionChoices = [(e.value, e.name) for e in ActionEnum]

    class TestTypeEnum(enum.Enum):
        UNK = 10
        ANTIGEN = 20
        RTPCR = 30
        CBNAAT = 40
        TRUENAT = 50
        RTLAMP = 60
        POCPCR = 70

    TestTypeChoices = [(e.value, e.name) for e in TestTypeEnum]

    source = models.IntegerField(choices=SourceChoices, default=SourceEnum.CARE.value)
    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True)
    nearest_facility = models.ForeignKey(
        "Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="nearest_facility",
    )
    meta_info = models.OneToOneField(
        "PatientMetaInfo", on_delete=models.SET_NULL, null=True
    )

    name = models.CharField(max_length=200, default="")

    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)

    phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator], default=""
    )

    emergency_phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator], default=""
    )

    address = models.TextField(default="")
    permanent_address = models.TextField(default="")

    pincode = models.IntegerField(default=0, blank=True, null=True)

    date_of_birth = models.DateField(default=None, null=True)
    year_of_birth = models.IntegerField(validators=[MinValueValidator(1900)], null=True)
    death_datetime = models.DateTimeField(default=None, null=True)

    nationality = models.CharField(
        max_length=255, default="", verbose_name="Nationality of Patient"
    )
    passport_no = models.CharField(
        max_length=255,
        default="",
        verbose_name="Passport Number of Foreign Patients",
    )
    ration_card_category = models.CharField(
        choices=RationCardCategory, null=True, max_length=8
    )

    is_medical_worker = models.BooleanField(
        default=False, verbose_name="Is the Patient a Medical Worker"
    )

    blood_group = models.CharField(
        choices=BLOOD_GROUP_CHOICES,
        null=True,
        blank=False,
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
        null=True,
        blank=True,
        verbose_name="Countries Patient has Travelled to",
    )
    date_of_return = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Return Date from the Last Country if Travelled",
    )

    allergies = models.TextField(
        default="", blank=True, verbose_name="Patient's Known Allergies"
    )

    present_health = models.TextField(
        default="", blank=True, verbose_name="Patient's Current Health Details"
    )
    ongoing_medication = models.TextField(
        default="",
        blank=True,
        verbose_name="Already pescribed medication if any",
    )
    has_SARI = models.BooleanField(  # noqa: N815
        default=False, verbose_name="Does the Patient Suffer from SARI"
    )

    is_antenatal = models.BooleanField(
        default=None, verbose_name="Does the patient require Prenatal Care ?"
    )
    last_menstruation_start_date = models.DateField(
        default=None, null=True, verbose_name="Last Menstruation Start Date"
    )
    date_of_delivery = models.DateField(
        default=None, null=True, verbose_name="Date of Delivery"
    )

    ward_old = models.CharField(
        max_length=255, default="", verbose_name="Ward of Patient", blank=False
    )

    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)
    local_body = models.ForeignKey(
        LocalBody, on_delete=models.SET_NULL, null=True, blank=True
    )
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True
    )
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    is_migrant_worker = models.BooleanField(
        default=False,
        verbose_name="Is Patient a Migrant Worker",
    )

    disease_status = models.IntegerField(
        choices=DISEASE_STATUS_CHOICES,
        default=1,
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

    last_edited = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="patient_last_edited_by",
    )

    action = models.IntegerField(
        choices=ActionChoices, blank=True, null=True, default=ActionEnum.NO_ACTION.value
    )
    review_time = models.DateTimeField(
        null=True, blank=True, verbose_name="Patient's next review time"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="patient_created_by",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Not active when discharged, or removed from the watchlist",
    )

    date_of_receipt_of_information = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Patient's information received date",
    )

    test_id = models.CharField(default="", max_length=100, null=True, blank=True)

    # Issue #600 Care_Fe
    date_of_test = models.DateTimeField(
        null=True, blank=True, verbose_name="Patient's test Date"
    )
    srf_id = models.CharField(max_length=200, blank=True, default="")
    test_type = models.IntegerField(
        choices=TestTypeChoices, default=TestTypeEnum.UNK.value
    )

    allow_transfer = models.BooleanField(default=False)

    last_consultation = models.ForeignKey(
        PatientConsultation, on_delete=models.SET_NULL, null=True, default=None
    )

    will_donate_blood = models.BooleanField(
        default=None,
        null=True,
        verbose_name="Is Patient Willing to donate Blood",
    )

    fit_for_blood_donation = models.BooleanField(
        default=None,
        null=True,
        verbose_name="Is Patient fit for donating Blood",
    )

    # IDSP REQUIREMENTS
    village = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Vilalge Name of Patient (IDSP Req)",
        null=True,
        blank=True,
    )
    designation_of_health_care_worker = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Designation of Health Care Worker (IDSP Req)",
        null=True,
        blank=True,
    )
    instituion_of_health_care_worker = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Institution of Healtcare Worker (IDSP Req)",
        null=True,
        blank=True,
    )
    transit_details = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Transit Details (IDSP Req)",
        null=True,
        blank=True,
    )
    frontline_worker = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Front Line Worker (IDSP Req)",
        null=True,
        blank=True,
    )
    date_of_result = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        verbose_name="Patient's result Date",
    )
    number_of_primary_contacts = models.IntegerField(
        null=True,
        default=None,
        blank=True,
        verbose_name="Number of Primary Contacts",
    )
    number_of_secondary_contacts = models.IntegerField(
        null=True,
        default=None,
        blank=True,
        verbose_name="Number of Secondary Contacts",
    )
    # IDSP Requirements End

    # Vaccination Fields
    is_vaccinated = models.BooleanField(
        default=False,
        verbose_name="Is the Patient Vaccinated Against COVID-19",
    )
    number_of_doses = models.PositiveIntegerField(
        default=0,
        null=False,
        blank=False,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    vaccine_name = models.CharField(
        choices=VaccineChoices,
        default=None,
        null=True,
        blank=False,
        max_length=15,
    )

    covin_id = models.CharField(
        max_length=15,
        default=None,
        null=True,
        blank=True,
        verbose_name="COVID-19 Vaccination ID",
    )
    last_vaccinated_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Date Last Vaccinated"
    )

    # Extras
    cluster_name = models.CharField(
        max_length=255,
        default=None,
        verbose_name="Name/ Cluster of Contact",
        null=True,
        blank=True,
    )
    is_declared_positive = models.BooleanField(
        default=None,
        null=True,
        verbose_name="Is Patient Declared Positive",
    )
    date_declared_positive = models.DateTimeField(
        null=True, blank=True, verbose_name="Date Patient is Declared Positive"
    )

    # Permission Scopes

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank="True",
        related_name="root_patient_assigned_to",
    )

    history = HistoricalRecords(excluded_fields=["meta_info"])

    objects = BaseManager()

    @property
    def is_expired(self) -> bool:
        return self.death_datetime is not None

    def __str__(self):
        return f"{self.name} - {self.year_of_birth} - {self.get_gender_display()}"

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

        if self.date_of_birth:
            self.year_of_birth = self.date_of_birth.year

        self.date_of_receipt_of_information = (
            self.date_of_receipt_of_information
            if self.date_of_receipt_of_information is not None
            else timezone.now()
        )

        self._alias_recovery_to_recovered()
        super().save(*args, **kwargs)

    def get_age(self) -> str:
        start = self.date_of_birth or date(self.year_of_birth, 1, 1)
        end = (self.death_datetime or timezone.now()).date()

        delta = relativedelta(end, start)

        if delta.years > 0:
            year_str = f"{delta.years} year{pluralize(delta.years)}"
            return f"{year_str}"

        if delta.months > 0:
            month_str = f"{delta.months} month{pluralize(delta.months)}"
            day_str = (
                f" {delta.days} day{pluralize(delta.days)}" if delta.days > 0 else ""
            )
            return f"{month_str}{day_str}"

        if delta.days > 0:
            return f"{delta.days} day{pluralize(delta.days)}"

        return "0 days"

    def annotate_diagnosis_ids(*args, **kwargs):
        return ArrayAgg(
            "last_consultation__diagnoses__diagnosis_id",
            filter=models.Q(*args, **kwargs),
        )

    CSV_ANNOTATE_FIELDS = {
        # Principal Diagnoses
        "principal_diagnoses": annotate_diagnosis_ids(
            last_consultation__diagnoses__is_principal=True
        ),
        "unconfirmed_diagnoses": annotate_diagnosis_ids(
            last_consultation__diagnoses__verification_status=ConditionVerificationStatus.UNCONFIRMED
        ),
        "provisional_diagnoses": annotate_diagnosis_ids(
            last_consultation__diagnoses__verification_status=ConditionVerificationStatus.PROVISIONAL
        ),
        "differential_diagnoses": annotate_diagnosis_ids(
            last_consultation__diagnoses__verification_status=ConditionVerificationStatus.DIFFERENTIAL
        ),
        "confirmed_diagnoses": annotate_diagnosis_ids(
            last_consultation__diagnoses__verification_status=ConditionVerificationStatus.CONFIRMED
        ),
    }

    CSV_MAPPING = {
        # Patient Details
        "external_id": "Patient ID",
        "facility__name": "Facility Name",
        "gender": "Gender",
        "age": "Age",
        "created_date": "Date of Registration",
        "created_date__time": "Time of Registration",
        # Last Consultation Details
        "last_consultation__route_to_facility": "Route to Facility",
        "last_consultation__created_date": "Date of first consultation",
        "last_consultation__created_date__time": "Time of first consultation",
        # Diagnosis Details
        "principal_diagnoses": "Principal Diagnosis",
        "unconfirmed_diagnoses": "Unconfirmed Diagnoses",
        "provisional_diagnoses": "Provisional Diagnoses",
        "differential_diagnoses": "Differential Diagnoses",
        "confirmed_diagnoses": "Confirmed Diagnoses",
        # Last Consultation Details
        "last_consultation__suggestion": "Decision after consultation",
        "last_consultation__category": "Category",
        "last_consultation__new_discharge_reason": "Reason for discharge",
        "last_consultation__discharge_date": "Date of discharge",
        "last_consultation__discharge_date__time": "Time of discharge",
    }

    def format_as_date(self):
        return self.strftime("%d/%m/%Y")

    def format_as_time(self):
        return self.strftime("%H:%M")

    def format_diagnoses(self):
        diagnoses = get_icd11_diagnoses_objects_by_ids(self)
        return ", ".join([diagnosis["label"] for diagnosis in diagnoses])

    CSV_MAKE_PRETTY = {
        "gender": (lambda x: REVERSE_GENDER_CHOICES[x]),
        "created_date": format_as_date,
        "created_date__time": format_as_time,
        "last_consultation__created_date": format_as_date,
        "last_consultation__created_date__time": format_as_time,
        "last_consultation__suggestion": (
            lambda x: PatientConsultation.REVERSE_SUGGESTION_CHOICES.get(x, "-")
        ),
        "principal_diagnoses": format_diagnoses,
        "unconfirmed_diagnoses": format_diagnoses,
        "provisional_diagnoses": format_diagnoses,
        "differential_diagnoses": format_diagnoses,
        "confirmed_diagnoses": format_diagnoses,
        "last_consultation__route_to_facility": (
            lambda x: REVERSE_ROUTE_TO_FACILITY_CHOICES.get(x, "-")
        ),
        "last_consultation__category": lambda x: REVERSE_CATEGORY_CHOICES.get(x, "-"),
        "last_consultation__new_discharge_reason": (
            lambda x: REVERSE_NEW_DISCHARGE_REASON_CHOICES.get(x, "-")
        ),
        "last_consultation__discharge_date": format_as_date,
        "last_consultation__discharge_date__time": format_as_time,
    }


class PatientMetaInfo(models.Model):
    class OccupationEnum(models.IntegerChoices):
        STUDENT = 1, "STUDENT"
        BUSINESSMAN = 2, "BUSINESSMAN"
        HEALTH_CARE_WORKER = 3, "HEALTH_CARE_WORKER"
        HEALTH_CARE_LAB_WORKER = 4, "HEALTH_CARE_LAB_WORKER"
        ANIMAL_HANDLER = 5, "ANIMAL_HANDLER"
        OTHERS = 6, "OTHERS"
        HEALTHCARE_PRACTITIONER = 7, "HEALTHCARE_PRACTITIONER"
        PARADEMICS = 8, "PARADEMICS"
        BUSINESS_RELATED = 9, "BUSINESS_RELATED"
        ENGINEER = 10, "ENGINEER"
        TEACHER = 11, "TEACHER"
        OTHER_PROFESSIONAL_OCCUPATIONS = 12, "OTHER_PROFESSIONAL_OCCUPATIONS"
        OFFICE_ADMINISTRATIVE = 13, "OFFICE_ADMINISTRATIVE"
        CHEF = 14, "CHEF"
        PROTECTIVE_SERVICE = 15, "PROTECTIVE_SERVICE"
        HOSPITALITY = 16, "HOSPITALITY"
        CUSTODIAL = 17, "CUSTODIAL"
        CUSTOMER_SERVICE = 18, "CUSTOMER_SERVICE"
        SALES_SUPERVISOR = 19, "SALES_SUPERVISOR"
        RETAIL_SALES_WORKER = 20, "RETAIL_SALES_WORKER"
        INSURANCE_SALES_AGENT = 21, "INSURANCE_SALES_AGENT"
        SALES_REPRESENTATIVE = 22, "SALES_REPRESENTATIVE"
        REAL_ESTATE = 23, "REAL_ESTATE"
        CONSTRUCTION_EXTRACTION = 24, "CONSTRUCTION_EXTRACTION"
        AGRI_NATURAL = 25, "AGRI_NATURAL"
        PRODUCTION_OCCUPATION = 26, "PRODUCTION_OCCUPATION"
        PILOT_FLIGHT = 27, "PILOT_FLIGHT"
        VEHICLE_DRIVER = 28, "VEHICLE_DRIVER"
        MILITARY = 29, "MILITARY"
        HOMEMAKER = 30, "HOMEMAKER"
        UNKNOWN = 31, "UNKNOWN"
        NOT_APPLICABLE = 32, "NOT_APPLICABLE"

    OccupationChoices = [(item.value, item.name) for item in OccupationEnum]

    class SocioeconomicStatus(models.IntegerChoices):
        VERY_POOR = 10, "VERY_POOR"
        POOR = 20, "POOR"
        MIDDLE_CLASS = 30, "MIDDLE_CLASS"
        WELL_OFF = 40, "WELL_OFF"

    class DomesticHealthcareSupport(models.IntegerChoices):
        NO_SUPPORT = 0, "NO_SUPPORT"
        FAMILY_MEMBER = 10, "FAMILY_MEMBER"
        PAID_CAREGIVER = 20, "PAID_CAREGIVER"

    occupation = models.IntegerField(choices=OccupationChoices, blank=True, null=True)
    socioeconomic_status = models.SmallIntegerField(
        choices=SocioeconomicStatus.choices, blank=True, null=True
    )
    domestic_healthcare_support = models.SmallIntegerField(
        choices=DomesticHealthcareSupport.choices, blank=True, null=True
    )
    head_of_household = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return f"PatientMetaInfo - {self.id}"


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
        # Touched body fluids of the patient (respiratory tract secretions/blood/vomit/saliva/urine/faces)
        TOUCHED_BODY_FLUIDS = 1
        # Had direct physical contact with the body of the patient including physical examination without full precautions.
        DIRECT_PHYSICAL_CONTACT = 2
        # Touched or cleaned the linens/clothes/or dishes of the patient
        CLEANED_USED_ITEMS = 3
        # Lives in the same household as the patient.
        LIVE_IN_SAME_HOUSEHOLD = 4
        # Close contact within 3ft (1m) of the confirmed case without precautions.
        CLOSE_CONTACT_WITHOUT_PRECAUTION = 5
        # Passenger of the aeroplane with a confirmed COVID -19 passenger for more than 6 hours.
        CO_PASSENGER_AEROPLANE = 6
        # Health care workers and other contacts who had full PPE while handling the +ve case
        HEALTH_CARE_WITH_PPE = 7
        # Shared the same space(same class for school/worked in same room/similar and not having a high risk exposure
        SHARED_SAME_SPACE_WITHOUT_HIGH_EXPOSURE = 8
        # Travel in the same environment (bus/train/Flight) but not having a high-risk exposure as cited above.
        TRAVELLED_TOGETHER_WITHOUT_HIGH_EXPOSURE = 9

    RelationChoices = [(item.value, item.name) for item in RelationEnum]
    ModeOfContactChoices = [(item.value, item.name) for item in ModeOfContactEnum]

    patient = models.ForeignKey(
        PatientRegistration,
        on_delete=models.PROTECT,
        related_name="contacted_patients",
    )
    patient_in_contact = models.ForeignKey(
        PatientRegistration,
        on_delete=models.PROTECT,
        null=True,
        related_name="contacts",
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

    def __str__(self):
        return f"{self.patient.name} - {self.patient_in_contact.name} - {self.get_relation_with_patient_display()}"


class Disease(models.Model):
    patient = models.ForeignKey(
        PatientRegistration,
        on_delete=models.CASCADE,
        related_name="medical_history",
    )
    disease = models.IntegerField(choices=DISEASE_CHOICES)
    details = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    objects = BaseManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "disease"],
                condition=models.Q(deleted=False),
                name="unique_patient_disease",
            )
        ]

    def __str__(self):
        return self.patient.name + " - " + self.get_disease_display()

    def get_disease_display(self):
        return DISEASE_CHOICES[self.disease - 1][1]


class PatientMobileOTP(BaseModel):
    is_used = models.BooleanField(default=False)
    phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator]
    )
    otp = models.CharField(max_length=10)


class PatientNoteThreadChoices(models.IntegerChoices):
    DOCTORS = 10, "DOCTORS"
    NURSES = 20, "NURSES"


class PatientNotes(FacilityBaseModel, ConsultationRelatedPermissionMixin):
    patient = models.ForeignKey(
        PatientRegistration, on_delete=models.PROTECT, null=False, blank=False
    )
    consultation = models.ForeignKey(
        PatientConsultation, on_delete=models.PROTECT, null=True, blank=True
    )
    facility = models.ForeignKey(
        Facility, on_delete=models.PROTECT, null=False, blank=False
    )
    user_type = models.CharField(max_length=25, default="")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    thread = models.SmallIntegerField(
        choices=PatientNoteThreadChoices,
        db_index=True,
        default=PatientNoteThreadChoices.DOCTORS,
    )
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    note = models.TextField(default="", blank=True)

    def get_related_consultation(self):
        # This is a temporary hack! this model does not have `assigned_to` field
        # and hence the permission mixin will fail if edit/object_read permissions are checked (although not used as of now)
        # Remove once patient notes is made consultation specific.
        return self


class PatientNotesEdit(models.Model):
    patient_note = models.ForeignKey(
        PatientNotes,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="edits",
    )
    edited_date = models.DateTimeField(auto_now_add=True)
    edited_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=False, blank=False
    )

    note = models.TextField()

    class Meta:
        ordering = ["-edited_date"]

    def __str__(self):
        return f"PatientNotesEdit {self.patient_note} - {self.edited_by}"


class PatientAgeFunc(Func):
    """
    Expression to calculate the age of a patient based on date of birth/year of
    birth and death date time.

    Eg:

    ```
    PatientSample.objects.annotate(patient_age=PatientAgeFunc())
    ```
    """

    function = "date_part"

    def __init__(self) -> None:
        super().__init__(
            Value("year"),
            Func(
                Case(
                    When(patient__death_datetime__isnull=True, then=Now()),
                    default=F("patient__death_datetime__date"),
                ),
                Coalesce(
                    "patient__date_of_birth",
                    Func(
                        F("patient__year_of_birth"),
                        Value(1),
                        Value(1),
                        function="MAKE_DATE",
                        output_field=models.DateField(),
                    ),
                    output_field=models.DateField(),
                ),
                function="age",
            ),
            output_field=models.IntegerField(),
        )
