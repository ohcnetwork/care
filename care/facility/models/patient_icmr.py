from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.timezone import now

from care.facility.models import (
    DISEASE_CHOICES_MAP,
    SYMPTOM_CHOICES,
    PatientConsultation,
    PatientContactDetails,
    PatientRegistration,
    PatientSample,
    Symptom,
)


class PatientIcmr(PatientRegistration):
    class Meta:
        proxy = True

    def get_age_delta(self):
        start = self.date_of_birth or timezone.datetime(self.year_of_birth, 1, 1).date()
        end = (self.death_datetime or timezone.now()).date()
        return relativedelta(end, start)

    @property
    def age_years(self) -> int:
        return self.get_age_delta().year

    @property
    def age_months(self) -> int:
        return self.get_age_delta().months

    @property
    def email(self):
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
        unsafe_travel_days = 14
        if self.countries_travelled:
            return len(self.countries_travelled) != 0 and (
                self.date_of_return
                and (self.date_of_return.date() - now().date()).days
                <= unsafe_travel_days
            )
        return None

    @property
    def travel_end_date(self):
        return self.date_of_return.date() if self.date_of_return else None

    @property
    def travel_start_date(self):
        return None

    @property
    def contact_case_name(
        self,
    ):
        contact_case = self.contacted_patients.first()
        return "" if not contact_case else contact_case.name

    @property
    def was_quarantined(
        self,
    ):
        return None

    @property
    def quarantined_type(
        self,
    ):
        return None


class PatientSampleICMR(PatientSample):
    class Meta:
        proxy = True

    # Start Proxying to PatientIcmr Patient Registration Object
    @property
    def personal_details(self):
        instance = self.patient
        if instance is not None:
            instance.__class__ = PatientIcmr
        return instance

    # Proxy to this Serializer
    @property
    def specimen_details(self):
        return self

    # Proxy to this Serializer
    @property
    def patient_category(self):
        instance = self.consultation
        if instance is not None:
            instance.__class__ = PatientConsultationICMR
        return instance

    # Proxy to this Serializer
    @property
    def exposure_history(self):
        instance = self.patient
        if instance is not None:
            instance.__class__ = PatientIcmr
        return instance

    @property
    def medical_conditions(self):
        return self

    @property
    def collection_date(self):
        return self.date_of_sample.date() if self.date_of_sample else None

    @property
    def label(self):
        return ""

    @property
    def is_repeated_sample(self):
        return PatientSample.objects.filter(patient=self.patient).count() > 1

    @property
    def lab_name(self):
        return ""

    @property
    def lab_pincode(self):
        return ""

    @property
    def hospitalization_date(self):
        return (
            self.consultation.encounter_date.date()
            if self.consultation and self.consultation.encounter_date
            else None
        )

    @property
    def medical_conditions_list(self):
        return [
            item.disease
            for item in self.patient.medical_history.all()
            if item.disease != DISEASE_CHOICES_MAP["NO"]
        ]

    @property
    def symptoms(self):
        symptoms = []
        for symptom in self.consultation.symptoms:
            if symptom == Symptom.OTHERS:
                symptoms.append(self.consultation.other_symptoms)
            else:
                symptoms.append(symptom)

        return symptoms

    @property
    def date_of_onset_of_symptoms(self):
        if symptom := self.consultation.symptoms.first():
            return symptom.onset_date.date()
        return None


class PatientConsultationICMR(PatientConsultation):
    class Meta:
        proxy = True

    def is_symptomatic(self):
        return bool(
            SYMPTOM_CHOICES[0][0] not in self.symptoms.choices
            or self.symptoms_onset_date is not None
        )

    def symptomatic_international_traveller(
        self,
    ):
        unsafe_travel_days = 14
        return bool(
            self.patient.countries_travelled
            and len(self.patient.countries_travelled) != 0
            and (
                self.patient.date_of_return
                and (self.patient.date_of_return.date() - now().date()).days
                <= unsafe_travel_days
            )
            and self.is_symptomatic()
        )

    def symptomatic_contact_of_confirmed_case(
        self,
    ):
        return self.patient.contact_with_confirmed_carrier and self.is_symptomatic()

    def symptomatic_healthcare_worker(
        self,
    ):
        return self.patient.is_medical_worker and self.is_symptomatic()

    def hospitalized_sari_patient(self):
        return self.patient.has_SARI and self.admitted

    def asymptomatic_family_member_of_confirmed_case(
        self,
    ):
        return (
            self.patient.contact_with_confirmed_carrier
            and not self.is_symptomatic()
            and any(
                contact_patient.relation_with_patient
                == PatientContactDetails.RelationEnum.FAMILY_MEMBER.value
                for contact_patient in self.patient.contacted_patients.all()
            )
        )

    def asymptomatic_healthcare_worker_without_protection(
        self,
    ):
        return self.patient.is_medical_worker and not self.is_symptomatic()
