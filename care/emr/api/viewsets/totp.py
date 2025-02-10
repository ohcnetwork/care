from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pyotp import TOTP, random_base32
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet


class TOTPViewSet(EMRBaseViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Initialize TOTP setup for user",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "uri": {"type": "string", "description": "TOTP URI for QR code"},
                    "secret_key": {"type": "string", "description": "TOTP secret key"},
                },
            }
        },
    )
    @action(detail=False, methods=["GET"])
    def setup(self, request):
        user = request.user

        if user.totp_secret:
            return Response(
                {"error": "TOTP is already configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = random_base32()

        totp = TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="CARE")

        user.totp_secret = secret
        user.save(update_fields=["totp_secret"])

        return Response({"uri": uri, "secret_key": secret})

    @extend_schema(
        description="Verify TOTP code and enable 2FA",
        request={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6-digit TOTP code"}
            },
        },
        responses={
            200: {"type": "object", "properties": {"message": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(detail=False, methods=["POST"])
    def verify(self, request):
        user = request.user
        code = request.data.get("code")

        if not user.totp_secret:
            return Response(
                {"error": "TOTP not configured"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not code:
            return Response(
                {"error": "Code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        totp = TOTP(user.totp_secret)
        if totp.verify(code):
            mfa_settings = user.mfa_settings or {}
            mfa_settings["totp"] = {
                "enabled": True,
                "verified_at": timezone.now().isoformat(),
            }
            user.mfa_settings = mfa_settings
            user.save(update_fields=["mfa_settings"])

            return Response({"message": "TOTP verified and enabled successfully"})

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)
