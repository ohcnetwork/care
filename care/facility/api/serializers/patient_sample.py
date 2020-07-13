from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import PatientConsultation, PatientRegistration, Facility
from care.facility.models.patient_sample import SAMPLE_TYPE_CHOICES, PatientSample, PatientSampleFlow
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


class PatientSampleFlowSerializer(serializers.ModelSerializer):
    status = ChoiceField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES, required=False)

    class Meta:
        model = PatientSampleFlow
        fields = "__all__"


class PatientSampleSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    patient_name = serializers.CharField(read_only=True, source="patient.name")
    patient_has_sari = serializers.BooleanField(read_only=True, source="patient.has_SARI")
    patient_has_confirmed_contact = serializers.BooleanField(
        read_only=True, source="patient.contact_with_confirmed_carrier"
    )
    patient_has_suspected_contact = serializers.BooleanField(
        read_only=True, source="patient.contact_with_suspected_carrier"
    )
    patient_travel_history = serializers.CharField(read_only=True, source="patient.countries_travelled")

    facility = ExternalIdSerializerField(read_only=True, source="consultation.facility")
    facility_object = FacilityBasicInfoSerializer(source="consultation.facility", read_only=True)

    sample_type = ChoiceField(choices=SAMPLE_TYPE_CHOICES, required=False)
    status = ChoiceField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES, required=False)
    result = ChoiceField(choices=PatientSample.SAMPLE_TEST_RESULT_CHOICES, required=False)

    icmr_category = ChoiceField(choices=PatientSample.PATIENT_ICMR_CATEGORY, required=False)

    patient = ExternalIdSerializerField(required=False, queryset=PatientRegistration.objects.all())
    consultation = ExternalIdSerializerField(required=False, queryset=PatientConsultation.objects.all())

    date_of_sample = serializers.DateTimeField(required=False)
    date_of_result = serializers.DateTimeField(required=False)

    notes = serializers.CharField(required=False, allow_blank=True)

    testing_facility = ExternalIdSerializerField(queryset=Facility.objects.all(), required=False)
    testing_facility_object = FacilityBasicInfoSerializer(source="testing_facility", read_only=True)

    class Meta:
        model = PatientSample
        read_only_fields = (
            "id",
            "facility",
        )
        exclude = TIMESTAMP_FIELDS + ("external_id",)

    def create(self, validated_data):
        validated_data.pop("status", None)
        validated_data.pop("result", None)

        return super(PatientSampleSerializer, self).create(validated_data)


class PatientSamplePatchSerializer(PatientSampleSerializer):
    notes = serializers.CharField(required=False)

    def update(self, instance, validated_data):
        try:
            is_completed = validated_data.get("result") in [1, 2]
            new_status = validated_data.get(
                "status", PatientSample.SAMPLE_TEST_FLOW_MAP["COMPLETED"] if is_completed else None
            )
            choice = PatientSample.SAMPLE_TEST_FLOW_CHOICES[new_status - 1][1]
            if is_completed:
                validated_data["status"] = PatientSample.SAMPLE_TEST_FLOW_MAP["COMPLETED"]
        except KeyError:
            raise ValidationError({"status": ["is required"]})
        valid_choices = PatientSample.SAMPLE_FLOW_RULES[PatientSample.SAMPLE_TEST_FLOW_CHOICES[instance.status - 1][1]]
        if choice not in valid_choices:
            raise ValidationError({"status": [f"Next valid choices are: {', '.join(valid_choices)}"]})
        if choice != "COMPLETED" and validated_data.get("result"):
            raise ValidationError({"result": [f"Result can't be updated unless test is complete"]})
        if choice == "COMPLETED" and not validated_data.get("result"):
            raise ValidationError({"result": [f"is required as the test is complete"]})

        if validated_data.get("result") is None and validated_data.get("date_of_result") is not None:
            raise ValidationError({"date_of_result": [f"cannot be provided without result"]})

        if not instance.date_of_sample and validated_data.get("status") in [
            PatientSample.SAMPLE_TEST_FLOW_MAP[key]
            for key in ["SENT_TO_COLLECTON_CENTRE", "RECEIVED_AND_FORWARED", "RECEIVED_AT_LAB"]
        ]:
            validated_data["date_of_sample"] = timezone.now()
        elif validated_data.get("status") == PatientSample.SAMPLE_TEST_FLOW_MAP["REQUEST_SUBMITTED"]:
            validated_data["result"] = PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"]
        elif validated_data.get("result") is not None and validated_data.get("date_of_result") is None:
            validated_data["date_of_result"] = timezone.now()

        return super().update(instance, validated_data)


class PatientSampleDetailSerializer(PatientSampleSerializer):
    flow = serializers.ListSerializer(child=PatientSampleFlowSerializer())
    facility_object = FacilityBasicInfoSerializer(source="consultation.facility")
