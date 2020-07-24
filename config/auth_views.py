from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate
from rest_framework import generics, status

from django.contrib.auth import get_user_model

from rest_framework import serializers

from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework_simplejwt.views import TokenViewBase

from config.ratelimit import ratelimit


User = get_user_model()


class CaptchaRequiredException(AuthenticationFailed):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _("Too Many Requests Provide Captcha")
    default_code = "captchaRequired"


class TokenObtainSerializer(serializers.Serializer):
    username_field = User.USERNAME_FIELD

    default_error_messages = {"no_active_account": _("No active account found with the given credentials")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        self.fields["password"] = PasswordField()

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass
        if ratelimit(self.context["request"], "login", [authenticate_kwargs[self.username_field]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        self.user = authenticate(**authenticate_kwargs)

        # Prior to Django 1.10, inactive users could be authenticated with the
        # default `ModelBackend`.  As of Django 1.10, the `ModelBackend`
        # prevents inactive users from authenticating.  App designers can still
        # allow inactive users to authenticate by opting for the new
        # `AllowAllUsersModelBackend`.  However, we explicitly prevent inactive
        # users from authenticating to enforce a reasonable policy and provide
        # sensible backwards compatibility with older Django versions.
        if self.user is None or not self.user.is_active:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account",
            )

        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplementedError("Must implement `get_token` method for `TokenObtainSerializer` subclasses")


class TokenObtainPairSerializer(TokenObtainSerializer):
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data


class TokenObtainPairView(TokenViewBase):
    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    serializer_class = TokenObtainPairSerializer

