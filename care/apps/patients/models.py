from django.db import models
from multiselectfield import MultiSelectField
from types import SimpleNamespace
from apps.accounts.models import (District,State,LocalBody)
from apps.commons.models import ActiveObjectsManager
from apps.facility.models import Facility
from apps.accounts.models import User
from apps.commons.constants import GENDER_CHOICES
from apps.commons.models import SoftDeleteTimeStampedModel
from apps.commons.validators import phone_number_regex
from fernet_fields import EncryptedCharField, EncryptedIntegerField, EncryptedTextField
from partial_index import PQ, PartialIndex
from apps.patients import constants
from simple_history.models import HistoricalRecords
from utils.models.jsonfield import JSONField

class Patient(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient
    """
    PATIENT_SEARCH_KEYS = ["name", "gender", "phone_number", "date_of_birth", "year_of_birth", "state_id"]
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
        (constants.DISEASE_STATUS_CHOICES.SU, 'SUSPECTED'),
        (constants.DISEASE_STATUS_CHOICES.PO, 'POSITIVE'),
        (constants.DISEASE_STATUS_CHOICES.NE, 'NEGATIVE'),
        (constants.DISEASE_STATUS_CHOICES.RE, 'RECOVERY'),
        (constants.DISEASE_STATUS_CHOICES.RD, 'RECOVERED'),
        (constants.DISEASE_STATUS_CHOICES.EX, 'EXPIRED'),
    ]
    SOURCE_CHOICES = [
        (constants.SOURCE_CHOICES.CA, 'CARE'),
        (constants.SOURCE_CHOICES.CT, 'COVID_TRACKER'),
        (constants.SOURCE_CHOICES.ST, 'STAY'),
    ]
    source = models.IntegerField(choices=SOURCE_CHOICES, default=constants.SOURCE_CHOICES.CA)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True)
    nearest_facility = models.ForeignKey(
        Facility, on_delete=models.SET_NULL, null=True, related_name="nearest_facility"
    )
    meta_info = models.OneToOneField("PatientMetaInfo", on_delete=models.SET_NULL, null=True)
    name = EncryptedCharField(max_length=200)
    age = models.PositiveIntegerField(null=True, blank=True)
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
    countries_travelled_old = models.TextField(
        null=True, blank=True, verbose_name="Countries Patient has Travelled to", editable=False
    )
    countries_travelled = JSONField(null=True, blank=True, verbose_name="Countries Patient has Travelled to")
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
        choices=DISEASE_STATUS_CHOICES, default=constants.DISEASE_STATUS_CHOICES.SU, blank=True, verbose_name="Disease Status"
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
    history = HistoricalRecords(excluded_fields=["patient_search_id", "meta_info"])

    objects = ActiveObjectsManager()

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
        self.date_of_receipt_of_information = (
            self.date_of_receipt_of_information
            if self.date_of_receipt_of_information is not None
            else datetime.datetime.now()
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

class PatientConsultation(SoftDeleteTimeStampedModel):
    """
    Model to represent a patientConsultation
    """
    ADMIT_CHOICES = [
        (constants.ADMIT_CHOICES.NA, "Not admitted"),
        (constants.ADMIT_CHOICES.IR, "Isolation Room"),
        (constants.ADMIT_CHOICES.ICU, "ICU"),
        (constants.ADMIT_CHOICES.ICV, "ICU with Ventilator"),
        (constants.ADMIT_CHOICES.HI, "Home Isolation"),
    ]    
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, related_name="patients")
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="facility")
    symptoms = MultiSelectField(choices=constants.SYMPTOM_CHOICES, default=1, null=True, blank=True)
    other_symptoms = models.TextField(default="", blank=True)
    symptoms_onset_date = models.DateTimeField(null=True, blank=True)
    category = models.CharField(choices=constants.CATEGORY_CHOICES, max_length=8, default=None, blank=True, null=True)
    examination_details = models.TextField(null=True, blank=True)
    existing_medication = models.TextField(null=True, blank=True)
    prescribed_medication = models.TextField(null=True, blank=True)
    suggestion = models.CharField(max_length=3, choices=constants.SUGGESTION_CHOICES)
    referred_to = models.ForeignKey(
        Facility, null=True, blank=True, on_delete=models.PROTECT, related_name="referred_patients",
    )
    admitted = models.BooleanField(default=False)
    admitted_to = models.IntegerField(choices=ADMIT_CHOICES, default=None, null=True, blank=True)
    admission_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    bed_number = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.patient.name}<>{self.facility.name}"

    def save(self, *args, **kwargs):
        if not self.pk or self.referred_to is not None:
            # pk is None when the consultation is created
            # referred to is not null when the person is being referred to a new facility
            self.patient.facility = self.referred_to or self.facility
            self.patient.save()

        super(PatientConsultation, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="if_referral_suggested",
                check=~models.Q(suggestion=constants.SuggestionChoices.R) | models.Q(referred_to__isnull=False),
            ),
            models.CheckConstraint(
                name="if_admitted", check=models.Q(admitted=False) | models.Q(admission_date__isnull=False),
            ),
        ]


class DailyRound(SoftDeleteTimeStampedModel):
    """
    Model to represent a daily round
    """
    CURRENT_HEALTH_CHOICES = [
        (constants.CURRENT_HEALTH_CHOICES.ND, "NO DATA"),
        (constants.CURRENT_HEALTH_CHOICES.RV, "REQUIRES VENTILATOR"),
        (constants.CURRENT_HEALTH_CHOICES.WR, "WORSE"),
        (constants.CURRENT_HEALTH_CHOICES.SQ, "STATUS QUO"),
        (constants.CURRENT_HEALTH_CHOICES.BT, "BETTER"),
    ]
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, related_name="daily_rounds")
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, default=0)
    temperature_measured_at = models.DateTimeField(null=True, blank=True)
    physical_examination_info = models.TextField(null=True, blank=True)
    additional_symptoms = MultiSelectField(choices=constants.SYMPTOM_CHOICES, default=1, null=True, blank=True)
    other_symptoms = models.TextField(default="", blank=True)
    patient_category = models.CharField(choices=constants.CATEGORY_CHOICES, max_length=8, default=None, blank=True, null=True)
    current_health = models.IntegerField(default=0, choices=CURRENT_HEALTH_CHOICES, blank=True)
    recommend_discharge = models.BooleanField(default=False, verbose_name="Recommend Discharging Patient")
    other_details = models.TextField(null=True, blank=True)


class PatientSampleTest(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient sample test
    """
    SAMPLE_TYPE_CHOICES = [
        (constants.SAMPLE_TYPE_CHOICES.UN, 'UNKNOWN'),
        (constants.SAMPLE_TYPE_CHOICES.BA, 'BA/ETA'),
        (constants.SAMPLE_TYPE_CHOICES.TS,"TS/NPS/NS"),
        (constants.SAMPLE_TYPE_CHOICES.BE, 'Blood_IN_EDTA'),
        (constants.SAMPLE_TYPE_CHOICES.AS, 'ACUTE_SERA'),
        (constants.SAMPLE_TYPE_CHOICES.CS, 'COVALESCENT_SERA'),
        (constants.SAMPLE_TYPE_CHOICES.OT, 'OTHER_TYPE'),
    ]   
    SAMPLE_TEST_FLOW_CHOICES = [
        (constants.SAMPLE_TEST_FLOW_MAP.RS, 'REQUEST_SUBMITTED'),
        (constants.SAMPLE_TEST_FLOW_MAP.AP, 'APPROVED'),
        (constants.SAMPLE_TEST_FLOW_MAP.DN, 'DENIED'),
        (constants.SAMPLE_TEST_FLOW_MAP.SC, 'SENT_TO_COLLECTON_CENTRE'),
        (constants.SAMPLE_TEST_FLOW_MAP.RF, 'RECEIVED_AND_FORWARED'),
        (constants.SAMPLE_TEST_FLOW_MAP.RL, 'RECEIVED_AT_LAB'),
        (constants.SAMPLE_TEST_FLOW_MAP.CT, 'COMPLETED'),
    ]
    SAMPLE_TEST_RESULT_CHOICES = [
        (constants.SAMPLE_TEST_RESULT_MAP.P, 'POSITIVE'),
        (constants.SAMPLE_TEST_RESULT_MAP.N, 'NEGATIVE'),
        (constants.SAMPLE_TEST_RESULT_MAP.A, 'AWAITING'),
        (constants.SAMPLE_TEST_RESULT_MAP.I, 'INVALID')
    ]
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    consultation = models.ForeignKey("PatientConsultation", on_delete=models.PROTECT)
    sample_type = models.IntegerField(choices=SAMPLE_TYPE_CHOICES,default=constants.SAMPLE_TYPE_CHOICES.UN)
    sample_type_other = models.TextField(default="")
    has_sari = models.BooleanField(default=False)
    has_ari = models.BooleanField(default=False)
    doctor_name = models.CharField(max_length=255, default="NO DOCTOR SPECIFIED")
    diagnosis = models.TextField(default="")
    diff_diagnosis = models.TextField(default="")
    etiology_identified = models.TextField(default="")
    is_atypical_presentation = models.BooleanField(default=False)
    atypical_presentation = models.TextField(default="")
    is_unusual_course = models.BooleanField(default=False)
    status = models.IntegerField(choices=constants.SAMPLE_TEST_FLOW_CHOICES, default=constants.SAMPLE_TEST_FLOW_MAP.RS)
    result = models.IntegerField(choices=SAMPLE_TEST_RESULT_CHOICES, default=constants.SAMPLE_TEST_RESULT_MAP.A)
    fast_track = models.TextField(default="")
    date_of_sample = models.DateTimeField(null=True, blank=True)
    date_of_result = models.DateTimeField(null=True, blank=True)

    @property
    def flow(self):
        try:
            return self.flow_prefetched
        except AttributeError:
            return self.patientsampleflow_set.order_by("-created_date")


class PatientSampleFlow(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient sample flow
    """
    patient_sample = models.ForeignKey(PatientSampleTest, on_delete=models.PROTECT)
    status = models.IntegerField(choices=PatientSampleTest.SAMPLE_TEST_FLOW_CHOICES)
    notes = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)


class PatientSearch(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient Search
    """
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

    @property
    def facility_id(self):
        facility_ids = Patient.objects.filter(id=self.patient_id).values_list("facility__external_id")
        return facility_ids[0][0] if len(facility_ids) > 0 else None


class PatientMetaInfo(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient meta info
    """
    OCCUPATION_CHOICES = [
        (constants.OCCUPATION_CHOICES.MW, 'STUDENT'),
        (constants.OCCUPATION_CHOICES.MW, 'MEDICAL_WORKER'),
        (constants.OCCUPATION_CHOICES.MW, 'GOVT_EMPLOYEE'),
        (constants.OCCUPATION_CHOICES.MW, 'PRIVATE_EMPLOYEE'),
        (constants.OCCUPATION_CHOICES.MW, 'HOME_MAKER'),
        (constants.OCCUPATION_CHOICES.MW, 'WORKING_ABROAD'),
        (constants.OCCUPATION_CHOICES.MW, ' OTHERS'),
    ]    
    occupation = models.IntegerField(choices=OCCUPATION_CHOICES)
    head_of_household = models.BooleanField()


class PatientContactDetails(SoftDeleteTimeStampedModel):
    """
    Model to represent a patient contact details
    """
    RELATION_CHOICES = [
        (constants.RELATION_CHOICES.FM, 'FAMILY_MEMBER'),
        (constants.RELATION_CHOICES.FR, 'FRIEND'),
        (constants.RELATION_CHOICES.RL, 'RELATIVE'),
        (constants.RELATION_CHOICES.NG, 'NEIGHBOUR'),
        (constants.RELATION_CHOICES.TT, 'TRAVEL_TOGETHER'),
        (constants.RELATION_CHOICES.WH, 'WHILE_AT_HOSPITAL'),
        (constants.RELATION_CHOICES.WP, 'WHILE_AT_SHOP'),
        (constants.RELATION_CHOICES.WO, 'WHILE_AT_OFFICE_OR_ESTABLISHMENT'),
        (constants.RELATION_CHOICES.WP, 'WORSHIP_PLACE'),
        (constants.RELATION_CHOICES.OT, 'OTHERS'),
    ]
    MODE_CONTACT_CHOICES = [
        (constants.MODE_CONTACT_CHOICES.TBF, 'TOUCHED_BODY_FLUIDS'),
        (constants.MODE_CONTACT_CHOICES.DPC, 'DIRECT_PHYSICAL_CONTACT'),
        (constants.MODE_CONTACT_CHOICES.CUI, 'CLEANED_USED_ITEMS'),
        (constants.MODE_CONTACT_CHOICES.LSH, 'LIVE_IN_SAME_HOUSEHOLD'),
        (constants.MODE_CONTACT_CHOICES.CLWP, 'CLOSE_CONTACT_WITHOUT_PRECAUTION'),
        (constants.MODE_CONTACT_CHOICES.CPA, 'CO_PASSENGER_AEROPLANE'),
        (constants.MODE_CONTACT_CHOICES.HCWP, 'HEALTH_CARE_WITH_PPE'),
        (constants.MODE_CONTACT_CHOICES.SSWE, 'SHARED_SAME_SPACE_WITHOUT_HIGH_EXPOSURE'),
        (constants.MODE_CONTACT_CHOICES.TTWE, 'TRAVELLED_TOGETHER_WITHOUT_HIGH_EXPOSURE'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="contacted_patients")
    patient_in_contact = models.ForeignKey(
        Patient, on_delete=models.PROTECT, null=True, related_name="contacts"
    )
    relation_with_patient = models.IntegerField(choices=RELATION_CHOICES)
    mode_of_contact = models.IntegerField(choices=MODE_CONTACT_CHOICES)
    date_of_first_contact = models.DateField(null=True)
    date_of_last_contact = models.DateField(null=True)
    is_primary = models.BooleanField(help_text="If false, then secondary contact")
    condition_of_contact_is_symptomatic = models.BooleanField(
        help_text="While in contact, did the patient showing symptoms"
    )

    objects = ActiveObjectsManager()


class Disease(SoftDeleteTimeStampedModel):
    """
    Model to represent a disease associated with patient
    """
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medical_history")
    disease = models.IntegerField(choices=constants.DISEASE_CHOICES)
    details = models.TextField(blank=True, null=True)

    objects = ActiveObjectsManager()

    class Meta:
        indexes = [PartialIndex(fields=["patient", "disease"], unique=True, where=PQ(active=True))]


class FacilityPatientStatsHistory(SoftDeleteTimeStampedModel):
    """
    Model to represent a facility patient stats history
    """
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT)
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


class PatientIcmr(Patient):
    """
    proxy Model to represent a patient ICMR
    """
    class Meta:
        proxy = True

    @property
    def personal_details(self):
        return self

    @property
    def specimen_details(self):
        instance = self.patientsample_set.last()
        if instance is not None:
            instance.__class__ = PatientSampleIcmr
        return instance

    @property
    def patient_category(self):
        instance = self.consultations.last()
        if instance:
            instance.__class__ = PatientConsultationIcmr
        return instance

    @property
    def exposure_history(self):
        return self

    @property
    def medical_conditions(self):
        instance = self.patientsample_set.last()
        if instance is not None:
            instance.__class__ = PatientSampleICMR
        return instance

    @property
    def age_years(self):
        if self.date_of_birth is None and self.year_of_birth is None:
            age_years = self.age
        elif self.year_of_birth is not None:
            age_years = datetime.datetime.now().year - self.year_of_birth
        else:
            diff_days = (datetime.datetime.now().date() - self.date_of_birth).days
            age_years = int(diff_days / 365)
        return age_years

    @property
    def age_months(self):
        if self.date_of_birth is None or self.year_of_birth is None:
            age_months = 0
        else:
            diff_days = (datetime.datetime.now().date() - self.date_of_birth).days
            age_years = int(diff_days / 365)
            age_months = int((diff_days - age_years * 365) / 12)
        return age_months

    @property
    def email(self):
        return ""

    @property
    def pincode(self):
        return ""

    @property
    def local_body_name(self):
        return "" if self.local_body is None else self.local_body.name

    @property
    def district_name(self):
        return "" if self.district is None else self.district.name

    @property
    def state_name(self):
        return "" if self.state is None else self.state.name

    @property
    def has_travel_to_foreign_last_14_days(self):
        if self.countries_travelled:
            return len(self.countries_travelled) != 0 and (
                self.date_of_return and (self.date_of_return.date() - datetime.datetime.now().date()).days <= 14
            )

    @property
    def travel_end_date(self):
        return self.date_of_return.date() if self.date_of_return else None

    @property
    def travel_start_date(self):
        return None

    @property
    def contact_case_name(self,):
        contact_case = self.contacted_patients.first()
        return "" if not contact_case else contact_case.name

    @property
    def was_quarantined(self,):
        return None

    @property
    def quarantined_type(self,):
        return None


class PatientSampleIcmr(PatientSampleTest):
    """
    Model to represent a patient sample ICMR
    """
    class Meta:
        proxy = True

    @property
    def collection_date(self):
        return self.date_of_sample.date() if self.date_of_sample else None

    @property
    def label(self):
        return ""

    @property
    def is_repeated_sample(self):
        return None

    @property
    def lab_name(self):
        return ""

    @property
    def lab_pincode(self):
        return ""

    @property
    def hospitalization_date(self):
        return (
            self.consultation.admission_date.date() if self.consultation and self.consultation.admission_date else None
        )

    @property
    def medical_conditions(self):
        return [
            item.disease for item in self.patient.medical_history.all() if item.disease != constants.DISEASE_CHOICES_MAP.NO
        ]

    @property
    def symptoms(self):
        return [
            symptom
            for symptom in self.consultation.symptoms
            if constants.SYMPTOM_CHOICES[0][0] not in self.consultation.symptoms.choices.keys()
        ]

    @property
    def date_of_onset_of_symptoms(self):
        return (
            self.consultation.symptoms_onset_date.date()
            if self.consultation and self.consultation.symptoms_onset_date
            else None
        )


class PatientConsultationIcmr(PatientConsultation):
    """
    model to reprent patient consultation ICMR
    """
    class Meta:
        proxy = True

    def is_symptomatic(self):
        if constants.SYMPTOM_CHOICES[0][0] not in self.symptoms.choices.keys() or self.symptoms_onset_date is not None:
            return True
        else:
            return False

    def symptomatic_international_traveller(self,):
        return (
            len(self.patient.countries_travelled) != 0
            and (
                self.patient.date_of_return
                and (self.patient.date_of_return.date() - datetime.datetime.now().date()).days <= 14
            )
            and self.is_symptomatic()
        )

    def symptomatic_contact_of_confirmed_case(self,):
        return self.patient.contact_with_confirmed_carrier and self.is_symptomatic()

    def symptomatic_healthcare_worker(self,):
        return self.patient.is_medical_worker and self.is_symptomatic()

    def hospitalized_sari_patient(self):
        return self.patient.has_SARI and self.admitted

    def asymptomatic_family_member_of_confirmed_case(self,):
        return (
            self.patient.contact_with_confirmed_carrier
            and not self.is_symptomatic()
            and any(
                contact_patient.relation_with_patient == PatientContactDetails.RelationEnum.FAMILY_MEMBER.value
                for contact_patient in self.patient.contacted_patients.all()
            )
        )

    def asymptomatic_healthcare_worker_without_protection(self,):
        return self.patient.is_medical_worker and not self.is_symptomatic()

class PatientFacility(SoftDeleteTimeStampedModel):
    """
    model to represent patient facility
    """
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    symptoms = MultiSelectField(choices=constants.SYMPTOM_CHOICES)
    other_symptoms = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True, verbose_name="Reason for calling")
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.patient.name}<>{self.reason}"
