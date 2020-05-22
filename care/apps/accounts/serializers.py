from rest_framework.serializers import ModelSerializer

from apps.accounts import models as accounts_models


class UserSerializer(ModelSerializer):

    class Meta:
        model = accounts_models.User
        fields = '__all__'

class StateSerializer(ModelSerializer):

    class Meta:
        model = accounts_models.State
        fields = ['name']

class DistrictSerializer(ModelSerializer):
    state = StateSerializer()

    class Meta:
        model = accounts_models.District
        fields = ['state', 'name']


class LocalBodySerializer(ModelSerializer):
    district = DistrictSerializer()

    class Meta:
        model = accounts_models.LocalBody
        fields = ['district', 'name', 'body_type', 'localbody_code']
