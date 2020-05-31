from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.utils import IntegrityError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext as _

from rest_framework import serializers as rest_serializers
from rest_framework.authtoken.models import Token

from apps.accounts import (
    mailers as accounts_mailers,
    models as accounts_models,
)

User = get_user_model()


class UserSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = accounts_models.User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "local_body",
            "age",
            "gender",
            "phone_number",
            "district",
            "user_type",
            "preferred_districts",
        )


class UserTypeSerializer(rest_serializers.ModelSerializer):
    """
    User type serializer
    """

    class Meta:
        model = accounts_models.UserType
        fields = (
            "id",
            "name",
        )


class StateSerializer(rest_serializers.ModelSerializer):
    """
    Serializer for state model
    """

    class Meta:
        model = accounts_models.State
        fields = (
            "id",
            "name",
        )


class DistrictSerializer(rest_serializers.ModelSerializer):
    """
    Serializer for state model
    """

    class Meta:
        model = accounts_models.District
        fields = ("id", "name", "state_id")


class LoginSerializer(rest_serializers.Serializer):
    """
    User login serializer
    """

    email = rest_serializers.CharField(label=_("Email"))
    password = rest_serializers.CharField(
        label=_("Password"), style={"input_type": "password"}
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = accounts_models.User.objects.filter(email=email).first()
            if not user or not user.check_password(password):
                msg = _(
                    "Your Email or Password is incorrect.Please try again, or click Forgot Password."
                )
                raise rest_serializers.ValidationError(msg)
        else:
            msg = _("Email/Password parameter is missing or invalid.")
            raise rest_serializers.ValidationError(msg)

        attrs["user"] = user
        return attrs


class LoginResponseSerializer(rest_serializers.ModelSerializer):
    """
    User login response serializer
    """

    token = rest_serializers.SerializerMethodField()

    class Meta:
        model = accounts_models.User
        fields = ("id", "token")

    def get_token(self, instance):
        token, _ = Token.objects.get_or_create(user=instance)
        return token.key


class LocalBodySerializer(rest_serializers.ModelSerializer):
    district = DistrictSerializer()

    class Meta:
        model = accounts_models.LocalBody
        fields = ("district", "name", "body_type", "localbody_code")


class ForgotPasswordLinkSerializer(rest_serializers.Serializer):
    """
    Serializer for sending reset password link
    """

    email = rest_serializers.EmailField()

    def validate_email(self, email):
        self.user = User.all_objects.filter(email=email).first()
        if not self.user:
            raise rest_serializers.ValidationError(
                "This email does not exist in our records"
            )
        return email

    def save(self):
        """
        Generates a one-use only link for resetting password and sends to the user.
        """
        accounts_mailers.ForgotPasswordMailer(
            user=self.user,
            uid=urlsafe_base64_encode(force_bytes(self.user.pk)),
            token=default_token_generator.make_token(self.user),
        ).send()


class BaseSetPasswordSerializer(rest_serializers.ModelSerializer):
    """
    Base Serializer for setting password
    """

    password_1 = rest_serializers.CharField(write_only=True)
    password_2 = rest_serializers.CharField(write_only=True)

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if validated_data.get("password_1") != validated_data.get("password_2"):
            raise rest_serializers.ValidationError("The two passwords do not match")
        return validated_data

    class Meta:
        fields = (
            "password_1",
            "password_2",
        )


class ResetPasswordSerializer(BaseSetPasswordSerializer):
    class Meta:
        model = User
        fields = BaseSetPasswordSerializer.Meta.fields

    def save(self):
        user = self.instance
        user.set_password(self.validated_data.get("password_1"))
        user.is_active = True
        try:
            user.save()
        except IntegrityError:
            raise rest_serializers.ValidationError(
                "Some Error Occurred. Please try again later."
            )
        return user
