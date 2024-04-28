import json
import logging
from datetime import datetime

import jwt
import requests
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.authentication import BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.tokens import Token

from care.facility.models import Facility
from care.facility.models.asset import Asset
from care.users.models import User

logger = logging.getLogger(__name__)


def jwk_response_cache_key(url: str) -> str:
    return f"jwk_response:{url}"


class MiddlewareUser(AnonymousUser):
    """
    Read-only user class for middleware authentication
    """

    def __init__(self, facility, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.facility = facility
        self.username = f"middleware{facility.external_id}"

    @property
    def is_authenticated(self):
        return True


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate_header(self, request):
        return ""

    def get_validated_token(self, raw_token):
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


class MiddlewareAuthentication(JWTAuthentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header.
    """

    facility_header = "X-Facility-Id"
    auth_header_type = "Middleware_Bearer"
    auth_header_type_bytes = auth_header_type.encode(HTTP_HEADER_ENCODING)

    def get_public_key(self, url):
        public_key_json = cache.get(jwk_response_cache_key(url))
        if not public_key_json:
            res = requests.get(url)
            res.raise_for_status()
            public_key_json = res.json()
            cache.set(jwk_response_cache_key(url), public_key_json, timeout=60 * 5)
        return public_key_json["keys"][0]

    def open_id_authenticate(self, url, token):
        public_key_response = self.get_public_key(url)
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(public_key_response)
        return jwt.decode(token, key=public_key, algorithms=["RS256"])

    def authenticate_header(self, request):
        return f'{self.auth_header_type} realm="{self.www_authenticate_realm}"'

    def get_user(self, _: Token, facility: Facility):
        return MiddlewareUser(facility=facility)

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None or self.facility_header not in request.headers:
            return None

        external_id = request.headers[self.facility_header]

        try:
            facility = Facility.objects.get(external_id=external_id)
        except (Facility.DoesNotExist, ValidationError) as e:
            raise InvalidToken({"detail": "Invalid Facility", "messages": []}) from e

        if not facility.middleware_address:
            raise InvalidToken({"detail": "Facility not connected to a middleware"})

        open_id_url = (
            f"https://{facility.middleware_address}/.well-known/openid-configuration/"
        )

        validated_token = self.get_validated_token(open_id_url, raw_token)

        return self.get_user(validated_token, facility), validated_token

    def get_raw_token(self, header):
        """
        Extracts an un-validated JSON web token from the given "Authorization"
        header value.
        """
        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            return None

        if parts[0] != self.auth_header_type_bytes:
            # Assume the header does not contain a JSON web token
            return None

        if len(parts) != 2:
            raise AuthenticationFailed(
                _("Authorization header must contain two space-delimited values"),
                code="bad_authorization_header",
            )

        return parts[1]

    def get_validated_token(self, url, raw_token):
        """
        Validates an encoded JSON web token and returns a validated token
        wrapper object.
        """
        try:
            return self.open_id_authenticate(url, raw_token)
        except Exception as e:
            logger.info(e, "Token: ", raw_token)

        raise InvalidToken({"detail": "Given token not valid for any token type"})


class MiddlewareAssetAuthentication(MiddlewareAuthentication):
    def get_user(self, validated_token, facility):
        """
        Attempts to find and return a user using the given validated token.
        """
        if "asset_id" not in validated_token:
            raise InvalidToken({"detail": "Given token does not contain asset_id"})

        try:
            asset_obj = Asset.objects.select_related("current_location__facility").get(
                external_id=validated_token["asset_id"]
            )
        except (Asset.DoesNotExist, ValidationError) as e:
            raise InvalidToken(
                {"detail": "Invalid Asset ID", "messages": [str(e)]}
            ) from e

        if asset_obj.current_location.facility != facility:
            raise InvalidToken({"detail": "Facility not connected to Asset"})

        # Create/Retrieve User and return them
        asset_user = User.objects.filter(asset=asset_obj).first()
        if not asset_user:
            password = User.objects.make_random_password()
            asset_user = User(
                username=f"asset{str(asset_obj.external_id)}",
                email="support@coronasafe.network",
                password=f"{password}123",  # The 123 makes it inaccessible without hashing
                gender=3,
                phone_number="919999999999",
                user_type=User.TYPE_VALUE_MAP["Nurse"],
                verified=True,
                asset=asset_obj,
                date_of_birth=datetime.now().date(),
            )
            asset_user.save()
        return asset_user


class ABDMAuthentication(JWTAuthentication):
    def open_id_authenticate(self, url, token):
        public_key = requests.get(url)
        jwk = public_key.json()["keys"][0]
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        return jwt.decode(
            token, key=public_key, audience="account", algorithms=["RS256"]
        )

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        jwt_token = request.META.get("HTTP_AUTHORIZATION")
        if jwt_token is None:
            return None
        jwt_token = self.get_jwt_token(jwt_token)

        abdm_cert_url = f"{settings.ABDM_URL}/gateway/v0.5/certs"
        validated_token = self.get_validated_token(abdm_cert_url, jwt_token)

        return self.get_user(validated_token), validated_token

    def get_jwt_token(self, token):
        return token.replace("Bearer", "").replace(" ", "")

    def get_validated_token(self, url, token):
        try:
            return self.open_id_authenticate(url, token)
        except Exception as e:
            logger.info(e, "Token: ", token)
            raise InvalidToken({"detail": f"Invalid Authorization token: {e}"})

    def get_user(self, validated_token):
        user = User.objects.filter(username=settings.ABDM_USERNAME).first()
        if not user:
            password = User.objects.make_random_password()
            user = User(
                username=settings.ABDM_USERNAME,
                email="hcx@coronasafe.network",
                password=f"{password}123",
                gender=3,
                phone_number="917777777777",
                user_type=User.TYPE_VALUE_MAP["Volunteer"],
                verified=True,
                date_of_birth=datetime.now().date(),
            )
            user.save()
        return user


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "config.authentication.CustomJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            header_name="Authorization", token_prefix="Bearer", bearer_format="JWT"
        )


class MiddlewareAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "config.authentication.MiddlewareAuthentication"
    name = "middlewareAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": _(
                "Used for authenticating requests from the middleware. "
                "The scheme requires a valid JWT token in the Authorization header "
                "along with the facility id in the X-Facility-Id header. "
                "--The value field is just for preview, filling it will show allowed "
                "endpoints.--"
            ),
        }


class MiddlewareAssetAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "config.authentication.MiddlewareAssetAuthentication"
    name = "middlewareAssetAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": _(
                "Used for authenticating requests from the middleware on behalf of assets. "
                "The scheme requires a valid JWT token in the Authorization header "
                "along with the facility id in the X-Facility-Id header. "
                "--The value field is just for preview, filling it will show allowed "
                "endpoints.--"
            ),
        }


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
