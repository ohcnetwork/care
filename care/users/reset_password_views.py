from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.signals import (
    post_password_reset,
    pre_password_reset,
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


class ResetPasswordConfirmSerializer(serializers.Serializer):
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
        try:
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data["token"]
        except Exception:
            raise

        if ratelimit(request, "reset", [token], "20/h"):
            return Response(
                {"detail": "Too Many Requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        # Verify token
        user, error_message = User.verify_password_reset_token(token)
        if not user:
            # Check if it's an expiration error
            if error_message == "Token has expired":
                return Response(
                    {"status": "expired", "detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"status": "invalid", "detail": error_message},
                status=status.HTTP_400_BAD_REQUEST,
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

        # Verify token and get user
        user, error_message = User.verify_password_reset_token(token)
        if not user:
            return Response(
                {"status": "invalid", "detail": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.context["user"] = user

        try:
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

        # Clear the reset flag to invalidate the token
        user.password_reset_required = False
        user.save(update_fields=["password", "password_reset_required"])

        post_password_reset.send(sender=self.__class__, user=user)
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

            # Set reset required flag to make this a one-time token
            user.password_reset_required = True
            user.save(update_fields=["password_reset_required"])
            token = user.generate_password_reset_token()
            self.send_password_reset_email(user, token)

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

    def send_password_reset_email(self, user, token):
        """
        Sends the password reset email to the user.
        """
        try:
            context = {
                "current_user": user,
                "username": user.username,
                "email": user.email,
                "reset_password_url": f"{settings.CURRENT_DOMAIN}/password_reset/{token}",
            }
            email_html_message = render_to_string(
                settings.USER_RESET_PASSWORD_EMAIL_TEMPLATE_PATH, context
            )
            msg = EmailMessage(
                "Password Reset for Care",
                email_html_message,
                settings.DEFAULT_FROM_EMAIL,
                (user.email,),
            )
            msg.content_subtype = "html"
            msg.send()
        except ValidationError as e:
            raise exceptions.ValidationError({"message": e.messages}) from e
