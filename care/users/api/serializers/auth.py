import contextlib

from django.contrib.auth import authenticate, get_user_model
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from care.utils.exceptions import CaptchaRequiredException
from config.ratelimit import ratelimit

User = get_user_model()


class TokenObtainSerializer(serializers.Serializer):
    username_field = User.USERNAME_FIELD

    default_error_messages = {
        "no_active_account": _("No active account found with the given credentials"),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField(write_only=True)
        self.fields["password"] = PasswordField()

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        with contextlib.suppress(KeyError):
            authenticate_kwargs["request"] = self.context["request"]

        if ratelimit(
            self.context["request"],
            "login",
            [authenticate_kwargs[self.username_field]],
        ):
            raise CaptchaRequiredException(
                detail={
                    "status": 429,
                    "detail": "Too Many Requests Provide Captcha",
                },
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
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplementedError(
            "Must implement `get_token` method for `TokenObtainSerializer` subclasses",
        )


class TokenRefreshSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])

        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    # Attempt to blacklist the given refresh token
                    refresh.blacklist()
                except AttributeError:
                    # If blacklist app not installed, `blacklist` method will
                    # not be present
                    pass

            refresh.set_jti()
            refresh.set_exp()

            data["refresh"] = str(refresh)

        # Updating users active status
        User.objects.filter(external_id=refresh["user_id"]).update(
            last_login=localtime(now()),
        )

        return data


class TokenObtainPairSerializer(TokenObtainSerializer):
    refresh = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)

    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        User.objects.filter(id=self.user.id).update(last_login=localtime(now()))

        return data
