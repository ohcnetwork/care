from rest_framework import serializers

from care.facility.models import DISEASE_CHOICES, SAMPLE_TYPE_CHOICES, SYMPTOM_CHOICES
from care.facility.models.patient_icmr import PatientConsultationICMR, PatientIcmr, PatientSampleICMR
from care.users.models import GENDER_CHOICES
from config.serializers import ChoiceField


class ICMRPersonalDetails(serializers.ModelSerializer):
    age_years = serializers.IntegerField()
    age_months = serializers.IntegerField()
    gender = ChoiceField(choices=GENDER_CHOICES)
    email = serializers.EmailField(allow_blank=True)
    pincode = serializers.CharField()

    local_body_name = serializers.CharField()
    district_name = serializers.CharField()
    state_name = serializers.CharField()

    class Meta:
        model = PatientIcmr
        fields = (
            "name",
            "gender",
            "age_years",
            "age_months",
            "date_of_birth",
            "phone_number",
            "email",
            "address",
            "pincode",
            "passport_no",
            # "aadhar_no",
            "local_body_name",
            "district_name",
            "state_name",
        )


class ICMRSpecimenInformationSerializer(serializers.ModelSerializer):
    sample_type = ChoiceField(choices=SAMPLE_TYPE_CHOICES)
    created_date = serializers.DateTimeField()
    label = serializers.CharField()
    is_repeated_sample = serializers.BooleanField(allow_null=True)
    lab_name = serializers.CharField()
    lab_pincode = serializers.CharField()

    icmr_category = ChoiceField(choices=PatientSampleICMR.PATIENT_ICMR_CATEGORY, required=False)

    class Meta:
        model = PatientSampleICMR
        fields = (
            "sample_type",
            "created_date",
            "label",
            "is_repeated_sample",
            "lab_name",
            "lab_pincode",
            "icmr_category",
            "icmr_label",
        )


class ICMRPatientCategorySerializer(serializers.ModelSerializer):
    symptomatic_international_traveller = serializers.BooleanField(allow_null=True)
    symptomatic_contact_of_confirmed_case = serializers.BooleanField(allow_null=True)
    symptomatic_healthcare_worker = serializers.BooleanField(allow_null=True)
    hospitalized_sari_patient = serializers.BooleanField(allow_null=True)
    asymptomatic_family_member_of_confirmed_case = serializers.BooleanField(allow_null=True)
    asymptomatic_healthcare_worker_without_protection = serializers.BooleanField(allow_null=True)

    class Meta:
        model = PatientConsultationICMR
        fields = (
            "symptomatic_international_traveller",
            "symptomatic_contact_of_confirmed_case",
            "symptomatic_healthcare_worker",
            "hospitalized_sari_patient",
            "asymptomatic_family_member_of_confirmed_case",
            "asymptomatic_healthcare_worker_without_protection",
        )


class ICMRExposureHistorySerializer(serializers.ModelSerializer):
    has_travel_to_foreign_last_14_days = serializers.BooleanField()
    places_of_travel = serializers.CharField(source="countries_travelled")
    travel_start_date = serializers.DateField()
    travel_end_date = serializers.DateField()

    contact_with_confirmed_case = serializers.BooleanField(source="contact_with_confirmed_carrier")
    contact_case_name = serializers.CharField()

    was_quarantined = serializers.BooleanField(allow_null=True)
    quarantined_type = serializers.CharField()

    healthcare_worker = serializers.BooleanField(source="is_medical_worker")

    class Meta:
        model = PatientIcmr
        fields = (
            "has_travel_to_foreign_last_14_days",
            "places_of_travel",
            "travel_start_date",
            "travel_end_date",
            "contact_with_confirmed_case",
            "contact_case_name",
            "was_quarantined",
            "quarantined_type",
            "healthcare_worker",
        )


class ICMRMedicalConditionSerializer(serializers.ModelSerializer):
    date_of_onset_of_symptoms = serializers.DateField()
    symptoms = serializers.ListSerializer(child=ChoiceField(choices=SYMPTOM_CHOICES))
    hospitalization_date = serializers.DateField()
    hospital_phone_number = serializers.CharField(source="consultation.facility.phone_number")
    hospital_name = serializers.CharField(source="consultation.facility.name")
    hospital_pincode = serializers.CharField(source="consultation.facility.pincode")

    medical_conditions_list = serializers.ListSerializer(child=ChoiceField(choices=DISEASE_CHOICES))

    class Meta:
        model = PatientSampleICMR
        fields = (
            # Section B.3
            "date_of_onset_of_symptoms",
            "symptoms",
            "has_sari",
            "has_ari",
            # Section B.4
            "medical_conditions_list",
            # Section B.5
            "hospitalization_date",
            "diagnosis",
            "diff_diagnosis",
            "etiology_identified",
            "is_atypical_presentation",
            "is_unusual_course",
            "hospital_phone_number",
            "hospital_name",
            "hospital_pincode",
            "doctor_name",
        )


class PatientICMRSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    personal_details = ICMRPersonalDetails()
    specimen_details = ICMRSpecimenInformationSerializer()
    patient_category = ICMRPatientCategorySerializer()
    exposure_history = ICMRExposureHistorySerializer()
    medical_conditions = ICMRMedicalConditionSerializer()

    class Meta:
        model = PatientSampleICMR
        fields = (
            "id",
            "personal_details",
            "specimen_details",
            "patient_category",
            "exposure_history",
            "medical_conditions",
        )
