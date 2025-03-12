from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenVerifyView, TokenViewBase

from config.ratelimit import ratelimit

User = get_user_model()

ACCESS_TOKEN_INVALIDATION_PREFIX = "ACCESS_TOKEN_INVALIDATE:"
REFRESH_TOKEN_INVALIDATION_PREFIX = "REFRESH_TOKEN_INVALIDATE:"


class CaptchaRequiredException(AuthenticationFailed):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _("Too Many Requests Provide Captcha")
    default_code = "captchaRequired"


class TokenObtainSerializer(serializers.Serializer):
    username_field = User.USERNAME_FIELD

    default_error_messages = {
        "no_active_account": _("No active account found with the given credentials")
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
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass
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
        msg = "Must implement `get_token` method for `TokenObtainSerializer` subclasses"
        raise NotImplementedError(msg)


class TokenRefreshSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])

        if refresh.get("temp_token"):
            raise PermissionDenied("Temporary tokens cannot be used to refresh")

        if cache.get(REFRESH_TOKEN_INVALIDATION_PREFIX + attrs["refresh"]):
            raise PermissionDenied("Invalid Token")

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
            last_login=localtime(now())
        )

        return data


class TokenObtainPairSerializer(TokenObtainSerializer):
    refresh = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)
    temp_token = serializers.CharField(read_only=True)

    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        totp_enabled = self.user.is_mfa_enabled()

        if totp_enabled:
            temp_token = RefreshToken.for_user(self.user)
            temp_token["temp_token"] = True
            temp_token.set_exp(lifetime=timedelta(minutes=5))

            return {
                "temp_token": str(temp_token),
            }
        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        User.objects.filter(id=self.user.id).update(last_login=localtime(now()))
        return data


class TokenObtainPairView(TokenViewBase):
    """
    Generate access and refresh tokens for a user.

    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    serializer_class = TokenObtainPairSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """
    Logout a user
    """

    def post(self, request, *args, **kwargs):
        if "access" not in request.data or "refresh" not in request.data:
            return Response({"detail": "Missing access or refresh token"}, status=400)
        try:
            refresh_token = RefreshToken(request.data["refresh"])
            refresh_token_payload = refresh_token.payload

            if refresh_token_payload["user_id"] != str(request.user.external_id):
                raise Exception("Invalid Token")

            access_token = AccessToken(request.data["access"])
            access_token_payload = access_token.payload

            if access_token_payload["user_id"] != str(request.user.external_id):
                raise Exception("Invalid Token")

            cache.set(
                ACCESS_TOKEN_INVALIDATION_PREFIX + request.data["access"],
                "1",
                timeout=1800,
            )
            cache.set(
                REFRESH_TOKEN_INVALIDATION_PREFIX + request.data["refresh"],
                "1",
                timeout=1800,
            )

        except:  # noqa E722
            return Response({}, status=400)
        return Response({})


class TokenRefreshView(TokenViewBase):
    """
    Refresh access token.

    Takes a refresh type JSON web token and returns an access type JSON web
    token if the refresh token is valid.
    """

    serializer_class = TokenRefreshSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AnnotatedTokenVerifyView(TokenVerifyView):
    """
    Verify tokens are valid.

    Takes a token and returns a boolean of whether it is a valid JSON web token
    for this project.
    """

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
