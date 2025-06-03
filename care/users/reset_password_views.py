from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.serializers import PasswordValidateMixin
from django_rest_passwordreset.signals import (
    post_password_reset,
    pre_password_reset,
)
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from care.users.models import PasswordResetToken
from config.ratelimit import ratelimit

User = get_user_model()

HTTP_USER_AGENT_HEADER = getattr(
    settings, "DJANGO_REST_PASSWORDRESET_HTTP_USER_AGENT_HEADER", "HTTP_USER_AGENT"
)
HTTP_IP_ADDRESS_HEADER = getattr(
    settings, "DJANGO_REST_PASSWORDRESET_IP_ADDRESS_HEADER", "REMOTE_ADDR"
)


class ResetPasswordCheckSerializer(serializers.Serializer):
    token = serializers.CharField(
        write_only=True, help_text="The token that was sent to the user's email address"
    )
    status = serializers.CharField(read_only=True, help_text="Request status")


class ResetPasswordConfirmSerializer(PasswordValidateMixin, serializers.Serializer):
    token = serializers.CharField(
        write_only=True, help_text="The token that was sent to the user's email address"
    )
    password = serializers.CharField(write_only=True, help_text="The new password")
    status = serializers.CharField(read_only=True, help_text="Request status")


class ResetPasswordRequestTokenSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    status = serializers.CharField(read_only=True, help_text="Request status")


class ResetPasswordCheck(GenericAPIView):
    """
    An Api View which provides a method to check if a password reset token is valid
    """

    authentication_classes = ()
    permission_classes = ()
    serializer_class = ResetPasswordCheckSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        if ratelimit(request, "reset", [token], "20/h"):
            return Response(
                {"detail": "Too Many Requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            token = PasswordResetToken.objects.get(key=token, is_used=False)
            if not token.is_valid():
                # Token has expired
                return Response(
                    {
                        "status": "expired",
                        "detail": "The password reset link has expired",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({"status": "OK"})
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"status": "notfound", "detail": "The password reset link is invalid"},
                status=status.HTTP_404_NOT_FOUND,
            )


class ResetPasswordConfirm(GenericAPIView):
    """
    An Api View which provides a method to reset a password based on a unique token
    """

    authentication_classes = ()
    permission_classes = ()
    serializer_class = ResetPasswordConfirmSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        token = serializer.validated_data["token"]

        if ratelimit(request, "reset", [token], "20/h"):
            return Response(
                {"detail": "Too Many Requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Find token
        try:
            token = PasswordResetToken.objects.get(key=token, is_used=False)

            # Check if token is valid
            if not token.is_valid():
                return Response(
                    {"status": "expired", "detail": "Token has expired"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = token.user
            serializer.context["user"] = user

            # Validate the password again with the user context
            try:
                validate_password(
                    password,
                    user=user,
                    password_validators=get_password_validators(
                        settings.AUTH_PASSWORD_VALIDATORS
                    ),
                )
            except ValidationError as e:
                # raise a validation error for the serializer
                raise exceptions.ValidationError({"password": e.messages}) from e

            pre_password_reset.send(sender=self.__class__, user=user)
            user.set_password(password)
            user.save()

            # Mark token as used
            token.is_used = True
            token.save()
            post_password_reset.send(sender=self.__class__, user=user)
            return Response({"status": "OK"})

        except PasswordResetToken.DoesNotExist:
            return Response(
                {"status": "invalid", "detail": "Invalid token"},
                status=status.HTTP_404_NOT_FOUND,
            )


class ResetPasswordRequestToken(GenericAPIView):
    """
    An Api View which provides a method to request a password reset token based on an e-mail address

    Sends a signal reset_password_token_created when a reset token was created
    """

    throttle_classes = ()
    authentication_classes = ()
    permission_classes = ()
    serializer_class = ResetPasswordRequestTokenSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]

        if ratelimit(request, "reset", [username]):
            return Response(
                {"detail": "Too Many Requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # if settings.IS_PRODUCTION and (
        #     not settings.EMAIL_HOST
        #     or not settings.EMAIL_HOST_USER
        #     or not settings.EMAIL_HOST_PASSWORD
        # ):
        #     raise exceptions.ValidationError(
        #         {
        #             "detail": [
        #                 _(
        #                     "There was a problem resetting your password. Please contact the administrator."
        #                 )
        #             ]
        #         }
        #     )
        # before we continue, delete all existing expired tokens
        # Find user by username or email
        users = User.objects.filter(username=username)
        if not users.exists():
            users = User.objects.filter(email=username)

        active_user_found = False
        # Clear expired tokens
        PasswordResetToken.clear_expired()

        # Get or create token for each matching user
        for user in users:
            if user.is_active:
                active_user_found = True
                # Invalidate existing tokens
                PasswordResetToken.objects.filter(user=user, is_used=False).update(
                    is_used=True
                )

                # Create new token
                PasswordResetToken.objects.create(
                    user=user,
                    user_agent=request.META.get(HTTP_USER_AGENT_HEADER, ""),
                    ip_address=request.META.get(HTTP_IP_ADDRESS_HEADER, ""),
                )
        if not active_user_found and not getattr(
            settings, "DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE", False
        ):
            raise exceptions.ValidationError(
                {
                    "username": [
                        _(
                            "There is no active user associated with this username or the password can not be changed"
                        )
                    ],
                }
            )

        return Response({"status": "OK"})
