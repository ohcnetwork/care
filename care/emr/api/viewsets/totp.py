from secrets import choice
from string import digits

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from pyotp import TOTP, random_base32
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet


class TOTPSetupResponse(BaseModel):
    uri: str
    secret_key: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPVerifyResponse(BaseModel):
    message: str
    backup_codes: list[str]


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

        totp = TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="CARE")

        user.totp_secret = secret
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

        totp = TOTP(user.totp_secret)
        if totp.verify(verify_data.code):
            backup_codes = self._generate_backup_codes()

            mfa_settings = user.mfa_settings or {}
            mfa_settings["totp"] = {
                "enabled": True,
                "verified_at": timezone.now().isoformat(),
                "backup_codes": [
                    {
                        "code": code,
                        "used": False,
                        "created_at": timezone.now().isoformat(),
                    }
                    for code in backup_codes
                ],
            }
            user.mfa_settings = mfa_settings
            user.save(update_fields=["mfa_settings"])

            response_data = TOTPVerifyResponse(
                message="Two-factor authentication has been enabled successfully. Please save your backup codes in a secure location.",
                backup_codes=backup_codes,
            )
            return Response(response_data.model_dump())

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)
