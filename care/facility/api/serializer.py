from rest_framework import serializers

from care.facility.models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for facility.models.Facility."""

    district = serializers.SerializerMethodField()
    facility_type = serializers.SerializerMethodField

    class Meta:
        model = Facility
        fields = [
            "name",
            "is_active",
            "verified",
            "district",
            "facility_type",
            "address",
            "phone_number",
            "created_by"]

    def get_district(self, facility_obj):
        """Return district value in human readable form."""
        return facility_obj.get_district_display()

    def get_facility_type(self, facility_obj):
        """Return facility_type in human readable form."""
        return facility_obj.get_facility_type_display()
