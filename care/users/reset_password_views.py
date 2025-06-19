from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.signals import (
    post_password_reset,
    pre_password_reset,
)
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework import exceptions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from care.emr.utils.reset_password import (
    send_password_reset_email,
    verify_password_reset_token,
)
from config.ratelimit import ratelimit

User = get_user_model()


class ResetPasswordCheckRequest(BaseModel):
    token: str = Field(
        ..., description="The token that was sent to the user's email address"
    )


class ResetPasswordCheckResponse(BaseModel):
    status: str = Field(..., description="Request status")


class ResetPasswordConfirmRequest(BaseModel):
    token: str = Field(
        ..., description="The token that was sent to the user's email address"
    )
    password: str = Field(..., description="The new password")


class ResetPasswordConfirmResponse(BaseModel):
    status: str = Field(..., description="Request status")


class ResetPasswordRequestTokenRequest(BaseModel):
    username: str


class ResetPasswordRequestTokenResponse(BaseModel):
    status: str = Field(..., description="Request status")


class ResetPasswordCheck(GenericAPIView):
    """
    An Api View which provides a method to check if a password reset token is valid
    """

    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        tags=["auth"],
        request=ResetPasswordCheckRequest,
        responses={200: ResetPasswordCheckResponse, 400: ResetPasswordCheckResponse},
    )
    def post(self, request, *args, **kwargs):
        try:
            data = ResetPasswordCheckRequest(**request.data)
            token = data.token
        except Exception as e:
            return Response(
                {"status": "error", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ratelimit(request, "reset", [token], "20/h"):
            return Response(
                {"detail": "Too Many Requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Verify token
        user, error_message = verify_password_reset_token(token)
        if not user:
            # Check if it's an expiration error
            if error_message == "Token has expired":
                response = ResetPasswordCheckResponse(
                    status="expired", detail=error_message
                ).model_dump()
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            response = ResetPasswordCheckResponse(
                status="invalid", detail=error_message
            ).model_dump()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        response = ResetPasswordCheckResponse(status="OK").model_dump()
        return Response(response)


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
            200: ResetPasswordConfirmResponse,
            400: ResetPasswordConfirmResponse,
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            data = ResetPasswordConfirmRequest(**request.data)
            password = data.password
            token = data.token
        except Exception as e:
            return Response(
                {"status": "error", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ratelimit(request, "reset", [token], "20/h"):
            return Response(
                {"detail": "Too Many Requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Verify token and get user
        user, error_message = verify_password_reset_token(token)
        if not user:
            response = ResetPasswordConfirmResponse(
                status="invalid", detail=error_message
            ).model_dump()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Django's built-in password validation
            validate_password(
                password,
                user=user,
                password_validators=get_password_validators(
                    settings.AUTH_PASSWORD_VALIDATORS
                ),
            )
        except ValidationError as e:
            raise exceptions.ValidationError({"password": e.messages}) from e

        # Reset password
        pre_password_reset.send(sender=self.__class__, user=user)
        user.set_password(password)
        user.save()  # Remove update_fields to ensure full save

        post_password_reset.send(sender=self.__class__, user=user)

        response = ResetPasswordConfirmResponse(status="OK").model_dump()
        return Response(response)


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
        responses={200: ResetPasswordRequestTokenResponse},
    )
    def post(self, request, *args, **kwargs):
        try:
            data = ResetPasswordRequestTokenRequest(**request.data)
            username = data.username
        except Exception as e:
            return Response(
                {"status": "error", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        active_user_found = False
        # Generate token for matching user
        if user and user.is_active:
            active_user_found = True
            send_password_reset_email(user)

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

        response = ResetPasswordRequestTokenResponse(status="OK").model_dump()
        return Response(response)
