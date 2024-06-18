from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.patient_vaccination import (
    PatientVaccination,
    VaccineRegistration,
)


class PatientVaccineRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineRegistration
        exclude = TIMESTAMP_FIELDS + ("id",)


class PatientCreateVaccinationSerializer(serializers.ModelSerializer):
    vaccine_name = serializers.CharField(write_only=True)

    class Meta:
        model = PatientVaccination
        fields = (
            "vaccine_name",
            "last_vaccinated_date",
            "dose_number",
            "vaccination_center",
            "batch_number",
        )


class PatientVaccinationSerializer(serializers.ModelSerializer):
    vaccine_name = PatientVaccineRegistrationSerializer()
    number_of_doses = serializers.CharField(source="dose_number")

    class Meta:
        model = PatientVaccination
        fields = (
            "vaccine_name",
            "number_of_doses",
            "batch_number",
            "last_vaccinated_date",
            "vaccination_center",
        )
