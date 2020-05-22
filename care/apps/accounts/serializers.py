from django.utils.translation import ugettext as _

from rest_framework import serializers as rest_serializers
from rest_framework.authtoken.models import Token

from apps.accounts import models as accounts_models


class UserSerializer(rest_serializers.ModelSerializer):

    class Meta:
        model = accounts_models.User
        fields = '__all__'


class StateSerializer(rest_serializers.ModelSerializer):
    """
    Serializer for state model
    """
    class Meta:
        model = accounts_models.State
        fields = ('name',)


class DistrictSerializer(rest_serializers.ModelSerializer):
    """
    Serializer for state model
    """
    class Meta:
        model = accounts_models.District
        fields = ('name',)


class LoginSerializer(rest_serializers.Serializer):
    """
    User login serializer
    """
    username = rest_serializers.CharField(label=_('User Name'))
    password = rest_serializers.CharField(label=_('Password'), style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = accounts_models.User.objects.filter(username=username).first()
            if not user or not user.check_password(password):
                msg = _('Your Email or Password is incorrect.Please try again, or click Forgot Password.')
                raise rest_serializers.ValidationError(msg)
        else:
            msg = _('Username/Password parameter is missing or invalid.')
            raise rest_serializers.ValidationError(msg)

        attrs['user'] = user
        return attrs


class LoginResponseSerializer(rest_serializers.ModelSerializer):
    """
    User login response serializer
    """
    token = rest_serializers.SerializerMethodField()

    class Meta:
        model = accounts_models.User
        fields = (
            'id', 'first_name', 'last_name', 'email', 'token', 'user_type', 'local_body',
        )

    def get_token(self, instance):
        token, _ = Token.objects.get_or_create(user=instance)
        return token.key
