from rest_framework import serializers

from care.facility.models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for facility.models.Facility."""
    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "is_active",
            "verified",
            "district",
            "facility_type",
            "address",
            "phone_number",
            "created_by"]
    
    def create(self, validated_data):
        return Facility.objects.create(**validated_data)