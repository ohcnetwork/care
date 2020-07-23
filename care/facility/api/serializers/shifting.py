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


class ShiftingSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    status = ChoiceField(choices=ShiftingRequest.STATUS_CHOICES)
    patient_obj = PatientListSerializer(source="patient")

    orgin_facility_object = FacilityBasicInfoSerializer(source="orgin_facility")
    shifting_approving_facility_object = FacilityBasicInfoSerializer(source="shifting_approving_facility")
    assigned_facility_object = FacilityBasicInfoSerializer(source="assigned_facility")

    orgin_facility = serializers.UUIDField(source="orgin_facility.external_id", allow_null=False, required=True)
    shifting_approving_facility = serializers.UUIDField(
        source="shifting_approving_facility.external_id", allow_null=False, required=True
    )
    assigned_facility = serializers.UUIDField(source="assigned_facility.external_id", allow_null=True, required=False)

    patient = serializers.UUIDField(source="patient.external_id", allow_null=False, required=True)

    class Meta:
        model = ShiftingRequest
        exclude = ("modified_date",)


class ShiftingDetailSerializer(ShiftingSerializer):

    patient = PatientDetailSerializer()

    class Meta:
        model = ShiftingRequest
        exclude = ("modified_date",)

