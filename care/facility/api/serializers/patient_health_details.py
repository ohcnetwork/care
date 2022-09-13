from django.forms import ChoiceField
from rest_framework import serializers

from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import (
    PatientConsultation,
    PatientHealthDetails,
    PatientRegistration,
)
from care.facility.models.facility import Facility
from care.facility.models.patient import Vaccine
from care.facility.models.patient_base import (
    BLOOD_GROUP_CHOICES,
    VACCINE_CHOICES,
)
from care.utils.serializer.external_id_field import ExternalIdSerializerField


class PatientHealthDetailsSerializer(serializers.ModelSerializer):
    class VaccinationHistorySerializer(serializers.Serializer):
        vaccine = serializers.ChoiceField(choices=VACCINE_CHOICES)
        doses = serializers.IntegerField(required=False, default=0)
        last_vaccinated_date = serializers.DateField()

        class Meta:
            model = Vaccine
            fields = (
                "vaccine",
                "doses",
                "last_vaccinated_date",
            )

    id = serializers.CharField(source="external_id", read_only=True)

    patient = ExternalIdSerializerField(
        queryset=PatientRegistration.objects.all()
    )
    facility = ExternalIdSerializerField(queryset=Facility.objects.all())
    facility_object = FacilityBasicInfoSerializer(
        source="facility", read_only=True
    )
    created_in_consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), required=False
    )
    blood_group = ChoiceField(choices=BLOOD_GROUP_CHOICES, required=True)

    vaccination_history = serializers.ListSerializer(
        child=VaccinationHistorySerializer(), required=False
    )

    class Meta:
        model = PatientHealthDetails
        exclude = ("deleted", "external_id")
