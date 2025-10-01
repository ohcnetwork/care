from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from care.emr.resources.common.mail_type import MailTypeChoices
from care.emr.resources.user.spec import (
    ResetPasswordCheckRequest,
    ResetPasswordConfirmRequest,
    ResetPasswordRequestTokenRequest,
    ResetPasswordResponse,
)
from care.emr.utils.reset_password import (
    send_password_reset_email,
    verify_password_reset_token,
)
from config.ratelimit import ratelimit

User = get_user_model()


class ResetPasswordCheck(GenericAPIView):
    """
    An Api View which provides a method to check if a password reset token is valid
    """

    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        tags=["auth"],
        request=ResetPasswordCheckRequest,
        responses={
            200: ResetPasswordResponse,
            404: ResetPasswordResponse,
            429: ResetPasswordResponse,
            400: ResetPasswordResponse,
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            data = ResetPasswordCheckRequest(**request.data)
            token = data.token
        except Exception:
            error_message = "Missing required parameter token."
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(
                response,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ratelimit(request, "reset-check", [token, "ip"], "10/h"):
            error_message = "Too many requests. Please try again later."
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(
                response,
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Verify token
        user, error_message = verify_password_reset_token(token)
        if not user:
            # Check if it's an expiration error
            if error_message == "Token has expired":
                response = ResetPasswordResponse(detail=error_message).model_dump()
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "OK"})


class ResetPasswordConfirm(GenericAPIView):
    """
    An Api View which provides a method to reset a password based on a unique token
    """

    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        tags=["auth"],
        request=ResetPasswordConfirmRequest,
        responses={
            200: ResetPasswordResponse,
            400: ResetPasswordResponse,
            429: ResetPasswordResponse,
            404: ResetPasswordResponse,
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            data = ResetPasswordConfirmRequest(**request.data)
            password = data.password
            token = data.token

        except Exception:
            error_message = "Missing required parameter token or password."
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(
                response,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ratelimit(request, "reset-confirm", [token, "ip"], "10/h"):
            error_message = "Too many requests. Please try again later."
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(
                response,
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Verify token and get user
        user, error_message = verify_password_reset_token(token)
        if not user:
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        validate_password(
            password,
            user=user,
            password_validators=get_password_validators(
                settings.AUTH_PASSWORD_VALIDATORS
            ),
        )
        user.set_password(password)
        user.save()

        return Response({"status": "OK"})


class ResetPasswordRequestToken(GenericAPIView):
    """
    An Api View which provides a method to request a password reset token based on an email/username
    """

    throttle_classes = ()
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        tags=["auth"],
        request=ResetPasswordRequestTokenRequest,
        responses={
            200: ResetPasswordResponse,
            400: ResetPasswordResponse,
            429: ResetPasswordResponse,
            404: ResetPasswordResponse,
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            data = ResetPasswordRequestTokenRequest(**request.data)
            username = data.username
        except Exception:
            error_message = "Missing required parameter username."
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if ratelimit(request, "reset-request", [username, "ip"], "10/h"):
            error_message = "Too many requests. Please try again later."
            response = ResetPasswordResponse(detail=error_message).model_dump()
            return Response(response, status=status.HTTP_429_TOO_MANY_REQUESTS)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        active_user_found = False
        # Generate token for matching user
        if user and user.is_active:
            active_user_found = True
            mail_type = MailTypeChoices.reset.value
            send_password_reset_email(user, mail_type)

        if not active_user_found and not getattr(
            settings, "DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE", False
        ):
            raise exceptions.ValidationError(
                {
                    "username": [
                        _(
                            "There is no active user associated with this username or the password cannot be changed"
                        )
                    ]
                }
            )

        return Response({"status": "OK"})
