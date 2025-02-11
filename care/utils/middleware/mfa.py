import logging
from datetime import timedelta

from django.http import JsonResponse
from django.urls import resolve
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


class MFAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # logger.info(f"MFA Middleware called for {request.method} {request.path}")

        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return self.get_response(request)

        # Skip MFA check for MFA-related endpoints
        current_url = resolve(request.path_info)
        if current_url.url_name in ["totp-setup", "totp-verify", "totp-verify-login"]:
            return self.get_response(request)

        # Get and validate token
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return self.get_response(request)

        try:
            token = auth_header.split(" ")[1]
            validated_token = AccessToken(token)
            # logger.info(f"Token claims: {validated_token.payload}")

            # Wait for authentication middleware to set user
            response = self.get_response(request)

            # Now check if user is authenticated
            if not request.user.is_authenticated:
                # logger.warning("User not authenticated after token validation")
                return JsonResponse(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # First check if this is a temporary token
            if validated_token.get("temp_token", False):
                if current_url.url_name != "mfa-totp-verify-login":
                    return JsonResponse(
                        {"error": "MFA verification required - temp token"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                return response

            # Then check MFA requirements
            mfa_settings = request.user.mfa_settings or {}
            totp_enabled = mfa_settings.get("totp", {}).get("enabled", False)

            if totp_enabled:
                # Verify MFA status
                mfa_verified = validated_token.get("mfa_verified", False)
                mfa_verified_at = validated_token.get("mfa_verified_at")

                if not mfa_verified or not mfa_verified_at:
                    # logger.warning("MFA required but not verified")
                    return JsonResponse(
                        {"error": "MFA verification required"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # Check if MFA verification is still valid
                verified_time = timezone.parse_datetime(mfa_verified_at)
                if timezone.now() - verified_time > timedelta(hours=12):
                    # logger.warning("MFA verification expired")
                    return JsonResponse(
                        {"error": "MFA verification expired"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # Verify token belongs to current user
                if str(validated_token.get("user_id")) != str(request.user.external_id):
                    # logger.warning("Token user mismatch")
                    return JsonResponse(
                        {"error": "Invalid token for user"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            return response

        except Exception as e:
            # logger.error(f"Token validation error: {e}")
            return JsonResponse(
                {"error": str(e) or "Invalid token"},
                status=status.HTTP_403_FORBIDDEN,
            )
