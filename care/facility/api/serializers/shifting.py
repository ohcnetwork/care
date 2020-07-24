from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import ShiftingRequest
from care.facility.models.patient_sample import SAMPLE_TYPE_CHOICES, PatientSample, PatientSampleFlow
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField

from care.facility.api.serializers.patient import PatientListSerializer, PatientDetailSerializer

from care.facility.api.serializers.facility import FacilityBasicInfoSerializer

from care.facility.models import Facility, PatientRegistration


class ShiftingSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    status = ChoiceField(choices=ShiftingRequest.STATUS_CHOICES)
    patient_object = PatientListSerializer(source="patient", read_only=True, required=False)

    orgin_facility_object = FacilityBasicInfoSerializer(source="orgin_facility", read_only=True, required=False)
    shifting_approving_facility_object = FacilityBasicInfoSerializer(
        source="shifting_approving_facility", read_only=True, required=False
    )
    assigned_facility_object = FacilityBasicInfoSerializer(source="assigned_facility", read_only=True, required=False)

    orgin_facility = serializers.UUIDField(source="orgin_facility.external_id", allow_null=False, required=True)
    shifting_approving_facility = serializers.UUIDField(
        source="shifting_approving_facility.external_id", allow_null=False, required=True
    )
    assigned_facility = serializers.UUIDField(source="assigned_facility.external_id", allow_null=True, required=False)

    patient = serializers.UUIDField(source="patient.external_id", allow_null=False, required=True)

    def create(self, validated_data):

        # Do Validity checks for each of these data

        orgin_facility_external_id = validated_data.pop("orgin_facility")["external_id"]
        validated_data["orgin_facility_id"] = Facility.objects.get(external_id=orgin_facility_external_id).id

        shifting_approving_facility_external_id = validated_data.pop("shifting_approving_facility")["external_id"]
        validated_data["shifting_approving_facility_id"] = Facility.objects.get(
            external_id=shifting_approving_facility_external_id
        ).id

        if "assigned_facility" in validated_data:
            assigned_facility_external_id = validated_data.pop("assigned_facility")["external_id"]
            if assigned_facility_external_id:
                validated_data["assigned_facility_id"] = Facility.objects.get(
                    external_id=assigned_facility_external_id
                ).id

        patient_external_id = validated_data.pop("patient")["external_id"]
        validated_data["patient_id"] = PatientRegistration.objects.get(external_id=patient_external_id).id

        return super().create(validated_data)

    class Meta:
        model = ShiftingRequest
        exclude = ("modified_date",)


class ShiftingDetailSerializer(ShiftingSerializer):

    patient = PatientDetailSerializer(read_only=True, required=False)

    class Meta:
        model = ShiftingRequest
        exclude = ("modified_date",)

