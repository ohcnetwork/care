from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import PatientConsultation, PatientRegistration, Facility
from care.facility.models.prescription_supplier import PrescriptionSupplier
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


class MinimalPatientSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id")

    class Meta:
        model = PatientRegistration
        fields = ("id", "name", "phone_number", "address")


class PrescriptionSupplierConsultationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)
    patient = MinimalPatientSerializer(read_only=True)

    class Meta:
        model = PatientConsultation
        fields = ("id", "prescriptions", "discharge_advice", "patient")


class PrescriptionSupplierSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)
    scheme = ChoiceField(choices=PrescriptionSupplier.SchemeChoices)
    status = ChoiceField(choices=PrescriptionSupplier.StatusChoices)
    consultation_object = PrescriptionSupplierConsultationSerializer(source="consultation", read_only=True)
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)

    consultation = ExternalIdSerializerField(required=True, queryset=PatientConsultation.objects.all())
    facility = ExternalIdSerializerField(required=True, queryset=Facility.objects.all())

    class Meta:
        model = PrescriptionSupplier
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.updated_user = self.context["request"].user
        instance.save()

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.updated_user = self.context["request"].user
        instance.save()
        return instance
