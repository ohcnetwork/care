from rest_framework.serializers import ModelSerializer

from apps.accounts import models as accounts_models


class UserSerializer(ModelSerializer):

    class Meta:
        model = accounts_models.User
        fields = '__all__'

class LocalBodySerializer(ModelSerializer):

    class Meta:
        model = accounts_models.LocalBody
        fields = '__all__'

class DistrictSerializer(ModelSerializer):

    class Meta:
        model = accounts_models.District
        fields = '__all__'


class StateSerializer(ModelSerializer):

    class Meta:
        model = accounts_models.State
        fields = '__all__'
