from rest_framework.serializers import ModelSerializer

from care.abdm.models import AbhaNumber


class AbhaSerializer(ModelSerializer):
    class Meta:
        exclude = ("deleted",)
        model = AbhaNumber
