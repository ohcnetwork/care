from rest_framework import serializers as rest_serializers

from apps.commons import models as commons_models


class OwnershipTypeSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = commons_models.OwnershipType
        fields = (
            "id",
            "name",
        )
