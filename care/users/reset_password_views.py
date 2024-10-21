from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.models import (
    ResetPasswordToken,
    clear_expired,
    get_password_reset_lookup_field,
    get_password_reset_token_expiry_time,
)
from django_rest_passwordreset.serializers import PasswordValidateMixin
from django_rest_passwordreset.signals import (
    post_password_reset,
    pre_password_reset,
    reset_password_token_created,
)
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

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

        # get token validation time
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # find token
        reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response(
                {"status": "notfound", "detail": "The password reset link is invalid"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # check expiry date
        expiry_date = reset_password_token.created_at + timedelta(
            hours=password_reset_token_validation_time
        )

        if timezone.now() > expiry_date:
            # delete expired token
            reset_password_token.delete()
            return Response(
                {"status": "expired", "detail": "The password reset link has expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"status": "OK"})


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

        # get token validation time
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # find token
        reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response(
                {"status": "notfound", "detail": "The password reset link is invalid"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # check expiry date
        expiry_date = reset_password_token.created_at + timedelta(
            hours=password_reset_token_validation_time
        )

        if timezone.now() > expiry_date:
            # delete expired token
            reset_password_token.delete()
            return Response(
                {"status": "expired", "detail": "The password reset link has expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # change users password (if we got to this code it means that the user is_active)
        if reset_password_token.user.eligible_for_reset():
            pre_password_reset.send(
                sender=self.__class__, user=reset_password_token.user
            )
            try:
                # validate the password against existing validators
                validate_password(
                    password,
                    user=reset_password_token.user,
                    password_validators=get_password_validators(
                        settings.AUTH_PASSWORD_VALIDATORS
                    ),
                )
            except ValidationError as e:
                # raise a validation error for the serializer
                raise exceptions.ValidationError({"password": e.messages}) from e

            reset_password_token.user.set_password(password)
            reset_password_token.user.save()
            post_password_reset.send(
                sender=self.__class__, user=reset_password_token.user
            )

        # Delete all password reset tokens for this user
        ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()

        return Response({"status": "OK"})


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

        if settings.IS_PRODUCTION and (
            not settings.EMAIL_HOST
            or not settings.EMAIL_HOST_USER
            or not settings.EMAIL_HOST_PASSWORD
        ):
            raise exceptions.ValidationError(
                {
                    "detail": [
                        _(
                            "There was a problem resetting your password. Please contact the administrator."
                        )
                    ]
                }
            )
        # before we continue, delete all existing expired tokens
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # datetime.now minus expiry hours
        now_minus_expiry_time = timezone.now() - timedelta(
            hours=password_reset_token_validation_time
        )

        # delete all tokens where created_at < now - 24 hours
        clear_expired(now_minus_expiry_time)

        # find a user
        users = User.objects.filter(
            **{f"{get_password_reset_lookup_field()}__exact": username}
        )

        active_user_found = False

        # iterate over all users and check if there is any user that is active
        # also check whether the password can be changed (is useable), as there could be users that are not allowed
        # to change their password (e.g., LDAP user)
        for user in users:
            if user.eligible_for_reset():
                active_user_found = True

        # No active user found, raise a validation error
        # but not if DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE == True
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

        # last but not least: iterate over all users that are active and can change their password
        # and create a Reset Password Token and send a signal with the created token
        for user in users:
            if user.eligible_for_reset():
                # define the token as none for now
                token = None

                # check if the user already has a token
                if user.password_reset_tokens.all().count() > 0:
                    # yes, already has a token, re-use this token
                    token = user.password_reset_tokens.all()[0]
                else:
                    # no token exists, generate a new token
                    token = ResetPasswordToken.objects.create(
                        user=user,
                        user_agent=request.META.get(HTTP_USER_AGENT_HEADER, ""),
                        ip_address=request.META.get(HTTP_IP_ADDRESS_HEADER, ""),
                    )
                # send a signal that the password token was created
                # let whoever receives this signal handle sending the email for the password reset
                reset_password_token_created.send(
                    sender=self.__class__, instance=self, reset_password_token=token
                )
        # done
        return Response({"status": "OK"})
