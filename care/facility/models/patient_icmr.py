import datetime
from dateutil.relativedelta import *
from care.facility.models import (
    DISEASE_CHOICES_MAP,
    SYMPTOM_CHOICES,
    PatientConsultation,
    PatientContactDetails,
    PatientRegistration,
    PatientSample,
)


class PatientIcmr(PatientRegistration):
    class Meta:
        proxy = True

    # @property
    # def personal_details(self):
    #     return self

    # @property
    # def specimen_details(self):
    #     instance = self.patientsample_set.last()
    #     if instance is not None:
    #         instance.__class__ = PatientSampleICMR
    #     return instance

    # @property
    # def patient_category(self):
    #     instance = self.consultations.last()
    #     if instance:
    #         instance.__class__ = PatientConsultationICMR
    #     return instance

    # @property
    # def exposure_history(self):
    #     return self

    # @property
    # def medical_conditions(self):
    #     instance = self.patientsample_set.last()
    #     if instance is not None:
    #         instance.__class__ = PatientSampleICMR
    #     return instance

    @property
    def age_years(self):
        if self.date_of_birth is not None:
            age_years = relativedelta(datetime.datetime.now(), self.date_of_birth).years
        else:
            age_years = relativedelta(
                datetime.datetime.now(), datetime.datetime(year=self.year_of_birth, month=1, day=1)
            ).years
        return age_years

    @property
    def age_months(self):
        if self.date_of_birth is None or self.year_of_birth is None:
            age_months = 0
        else:
            age_months = relativedelta(datetime.datetime.now(), self.date_of_birth).months
        return age_months

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
            self.consultation.admission_date.date() if self.consultation and self.consultation.admission_date else None
        )

    @property
    def medical_conditions_list(self):
        return [
            item.disease for item in self.patient.medical_history.all() if item.disease != DISEASE_CHOICES_MAP["NO"]
        ]

    @property
    def symptoms(self):
        return [
            symptom
            for symptom in self.consultation.symptoms
            # if SYMPTOM_CHOICES[0][0] not in self.consultation.symptoms.choices.keys()
        ]

    @property
    def date_of_onset_of_symptoms(self):
        return (
            self.consultation.symptoms_onset_date.date()
            if self.consultation and self.consultation.symptoms_onset_date
            else None
        )


class PatientConsultationICMR(PatientConsultation):
    class Meta:
        proxy = True

    def is_symptomatic(self):
        if SYMPTOM_CHOICES[0][0] not in self.symptoms.choices.keys() or self.symptoms_onset_date is not None:
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
