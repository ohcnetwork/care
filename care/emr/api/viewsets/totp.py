from secrets import choice
from string import digits

from celery import shared_task
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from pyotp import TOTP, random_base32
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.users.models import User
from care.utils.encryption import decrypt_string, encrypt_string


class TOTPSetupResponse(BaseModel):
    uri: str
    secret_key: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPVerifyResponse(BaseModel):
    message: str
    backup_codes: list[str]


class TOTPLoginRequest(BaseModel):
    code: str


class TOTPLoginResponse(BaseModel):
    message: str
    status: str


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    expires=10 * 60,
)
def send_totp_enabled_email(user_email: str, user_name: str):
    """Send email notification when TOTP is enabled"""
    context = {
        "username": user_name,
        "email": user_email,
        "enabled_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    email_html_message = render_to_string("email/totp_enabled.html", context)

    msg = EmailMessage(
        "Two-Factor Authentication Enabled",
        email_html_message,
        settings.DEFAULT_FROM_EMAIL,
        (user_email,),
    )
    msg.content_subtype = "html"
    msg.send()


class TOTPViewSet(EMRBaseViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Initialize TOTP setup for user",
        responses={
            200: TOTPSetupResponse,
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(detail=False, methods=["GET"])
    def setup(self, request):
        user = request.user

        mfa_settings = user.mfa_settings or {}
        totp_enabled = mfa_settings.get("totp", {}).get("enabled", False)

        if totp_enabled:
            return Response(
                {
                    "error": "Two-factor authentication is already set up and enabled for your account"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = random_base32()
        encrypted_secret = encrypt_string(secret)

        totp = TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="CARE")

        user.totp_secret = encrypted_secret
        user.save(update_fields=["totp_secret"])

        response_data = TOTPSetupResponse(uri=uri, secret_key=secret)
        return Response(response_data.model_dump())

    @staticmethod
    def _generate_backup_codes(count: int = 10) -> list[str]:
        """Generate 8-digit backup codes."""
        codes = []
        for _ in range(count):
            code = "".join(choice(digits) for _ in range(8))
            codes.append(code)
        return codes

    @extend_schema(
        description="Verify TOTP code and enable 2FA",
        request=TOTPVerifyRequest,
        responses={
            200: TOTPVerifyResponse,
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(detail=False, methods=["POST"])
    def verify(self, request):
        verify_data = TOTPVerifyRequest(code=request.data.get("code"))
        user = request.user

        if not user.totp_secret:
            return Response(
                {"error": "TOTP not configured"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not verify_data.code:
            return Response(
                {"error": "Code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        secret = decrypt_string(user.totp_secret)
        totp = TOTP(secret)

        if totp.verify(verify_data.code):
            backup_codes = self._generate_backup_codes()

            mfa_settings = user.mfa_settings or {}
            mfa_settings["totp"] = {
                "enabled": True,
                "totp_enabled_at": timezone.now().isoformat(),
                "backup_codes": [
                    {
                        "code": make_password(code),
                        "used": False,
                        "created_at": timezone.now().isoformat(),
                    }
                    for code in backup_codes
                ],
            }
            user.mfa_settings = mfa_settings
            user.save(update_fields=["mfa_settings"])

            send_totp_enabled_email.delay(user.email, user.username)

            response_data = TOTPVerifyResponse(
                message="Two-factor authentication has been enabled successfully. Please save your backup codes in a secure location.",
                backup_codes=backup_codes,
            )
            return Response(response_data.model_dump())

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Verify TOTP code during login",
        request=TOTPLoginRequest,
        responses={
            200: TOTPLoginResponse,
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        permission_classes=[],
        authentication_classes=[],
    )
    def login(self, request):
        code = request.data.get("code")
        temp_token = request.data.get("temp_token")

        if not code or not temp_token:
            return Response(
                {"error": "Code and temporary token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Validate the temporary token
            token = RefreshToken(temp_token)
            if not token.get("temp_token"):
                return Response(
                    {"error": "Invalid token type"}, status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(external_id=token["user_id"])
            totp = TOTP(decrypt_string(user.totp_secret))

            if totp.verify(code):
                refresh = RefreshToken.for_user(user)

                try:
                    token.blacklist()
                except AttributeError:
                    pass

                return Response(
                    {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    }
                )

            return Response(
                {"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
