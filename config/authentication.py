import logging

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from rest_framework.authentication import BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate_header(self, request):
        return ""

    def get_validated_token(self, raw_token):
        from config.auth_views import ACCESS_TOKEN_INVALIDATION_PREFIX

        if cache.get(ACCESS_TOKEN_INVALIDATION_PREFIX + raw_token.decode()):
            raise InvalidToken("Invalid Token")
        try:
            return super().get_validated_token(raw_token)
        except InvalidToken as e:
            raise InvalidToken(
                {
                    "detail": "Invalid Token, please relogin to continue",
                    "messages": e.detail.get("messages", []),
                }
            ) from e


class CustomBasicAuthentication(BasicAuthentication):
    def authenticate_header(self, request):
        return ""


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "config.authentication.CustomJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            header_name="Authorization",
            token_prefix="Bearer",
            bearer_format="JWT",
        )


class CustomBasicAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "config.authentication.CustomBasicAuthentication"
    name = "basicAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "basic",
            "description": _("Do not use this scheme for production."),
        }


class SessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "rest_framework.authentication.SessionAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
            "scheme": "http",
            "description": _("Do not use this scheme for production."),
        }
