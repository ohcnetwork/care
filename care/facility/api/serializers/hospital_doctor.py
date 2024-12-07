from rest_framework import serializers
from django.db.models import Sum

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import DOCTOR_TYPES, HospitalDoctors
from care.utils.serializers.fields import ChoiceField


class HospitalDoctorSerializer(serializers.ModelSerializer):
    area_text = ChoiceField(choices=DOCTOR_TYPES, read_only=True, source="area")
    id = serializers.UUIDField(source="external_id", read_only=True)
    total_doctors = serializers.IntegerField(read_only=True)

    class Meta:
        model = HospitalDoctors
        read_only_fields = (
            "id",
            "area_text",
            "total_doctors"
        )
        exclude = (*TIMESTAMP_FIELDS, "facility", "external_id")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            representation["total_doctors"] = (
                HospitalDoctors.objects.filter(facility=instance.facility)
                .aggregate(total_doctors=Sum("count"))["total_doctors"]
                or 0
            )
        except Exception as e:
            representation["total_doctors"] = 0
        return representation
