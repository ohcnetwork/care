import logging

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import (
    AuthenticationFailed,
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.tokens import RefreshToken

from care.users.models import User
from config.ratelimit import ratelimit

logger = logging.getLogger(__name__)


def validate_temp_token(temp_token: str) -> tuple[RefreshToken, str]:
    """Validate temporary token and return token object with user ID"""
    try:
        token = RefreshToken(temp_token)
        user_id = str(token["user_id"])

        if not token.get("temp_token"):
            raise InvalidToken({"detail": "Invalid token type"})

        return user_id
    except TokenError as e:
        raise InvalidToken({"detail": "Temp token is invalid or expired"}) from e
    except Exception as e:
        logger.error("Unexpected error during token validation: %s", e)
        raise InvalidToken({"detail": "Invalid token"}) from None


def check_mfa_ip_rate_limit(request):
    """Check IP-based rate limit"""
    if ratelimit(request, "mfa-login", ["ip"]):
        raise Throttled(detail="Too Many Requests. Please try again later.")


def check_mfa_user_rate_limit(request, user_id: str):
    """Check user-based rate limit"""
    if ratelimit(request, "mfa-login", [user_id]):
        raise Throttled(detail="Too Many Requests. Please try again later.")


def create_auth_response(user: User) -> Response:
    """Create authentication response with access and refresh tokens"""
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )


def verify_password(user: User, password: str):
    """Verify user password"""
    if not user.check_password(password):
        raise AuthenticationFailed
