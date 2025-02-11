from datetime import timedelta

from django.http import JsonResponse
from django.urls import resolve
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


class MFAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip MFA check for MFA-related endpoints
        current_url = resolve(request.path_info)
        if current_url.url_name in ["totp-setup", "totp-verify", "totp-verify-login"]:
            return self.get_response(request)

        # Check if user has MFA enabled
        mfa_settings = request.user.mfa_settings or {}
        totp_enabled = mfa_settings.get("totp", {}).get("enabled", False)

        if not totp_enabled:
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"error": "MFA verification required"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            token = auth_header.split(" ")[1]
            # This will verify signature and expiry
            validated_token = AccessToken(token)

            # Verify MFA status
            mfa_verified = validated_token.get("mfa_verified", False)
            mfa_verified_at = validated_token.get("mfa_verified_at")

            if not mfa_verified or not mfa_verified_at:
                raise TokenError("MFA not verified")

            # Check if MFA verification is still valid (e.g., within 12 hours)
            verified_time = timezone.parse_datetime(mfa_verified_at)
            if timezone.now() - verified_time > timedelta(hours=12):
                raise TokenError("MFA verification expired")

            # Verify token belongs to current user
            if str(validated_token["user_id"]) != str(request.user.external_id):
                raise TokenError("Invalid token for user")

            return self.get_response(request)

        except (TokenError, ValueError) as e:
            return JsonResponse(
                {"error": str(e) or "MFA verification required"},
                status=status.HTTP_403_FORBIDDEN,
            )
