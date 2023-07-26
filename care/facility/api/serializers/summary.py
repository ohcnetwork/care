from rest_framework import serializers

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.models import DistrictScopedSummary, FacilityRelatedSummary


class FacilitySummarySerializer(serializers.ModelSerializer):
    facility = FacilitySerializer()

    class Meta:
        model = FacilityRelatedSummary
        exclude = (
            "id",
            "s_type",
        )


class DistrictSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DistrictScopedSummary
        exclude = (
            "id",
            "s_type",
        )
