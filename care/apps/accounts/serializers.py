from rest_framework.serializers import ModelSerializer

from apps.accounts import models as accounts_models


class UserSerializer(ModelSerializer):

    class Meta:
        model = accounts_models.User
        fields = '__all__'
