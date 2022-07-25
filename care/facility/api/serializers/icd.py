from rest_framework import serializers

from care.facility.models.icd import ICDDisease


class ICDSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    label = serializers.CharField()
    is_leaf = serializers.BooleanField(write_only=True)
    class_kind = serializers.CharField()
    is_adopted_child = serializers.BooleanField()
    average_depth = serializers.FloatField()
    parent_id = serializers.CharField(allow_null=True)

    class Meta:
        model = ICDDisease
        fields = "__all__"
