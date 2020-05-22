from rest_framework import serializers

from apps.accounts import (
    models as accounts_models,
    serializers as accounts_serializers
)
from apps.facility import (
    models as facility_models
)


class FacilityListSerializer(serializers.ModelSerializer):
    local_body = accounts_serializers.LocalBodySerializer
    district = accounts_serializers.DistrictSerializer
    state = accounts_serializers.StateSerializer
    created_by = accounts_serializers.UserSerializer
    users = accounts_serializers.UserSerializer

    class Meta:
        model = facility_models.Facility
        fields = (
            'name', 'is_active', 'verified', 'facility_type', 'location', 'address',
            'local_body', 'district', 'state', 'oxygen_capacity', 'phone_number',
            'corona_testing', 'created_by', 'users'
        )
        depth = 1
