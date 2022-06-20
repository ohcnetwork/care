from rest_framework import serializers

from care.facility.models.icd import ICDDisease


class ICDSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=50, read_only=True)
    name = serializers.CharField(max_length=256)
    reference_url = serializers.CharField(max_length=256)

    def create(self, validated_data):
        return ICDDisease(id=None, **validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        return instance
