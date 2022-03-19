import json
from uuid import UUID

import jwt
import requests
from rest_framework.authentication import BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from care.facility.models import Facility


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate_header(self, request):
        return ""


class CustomBasicAuthentication(BasicAuthentication):
    def authenticate_header(self, request):
        return ""


class MiddlewareAuthentication(JWTAuthentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header.
    """

    FACILITY_HEADER = "X-Facility-Id"

    def open_id_authenticate(self, url, token):
        public_key = requests.get(url)
        jwk = public_key.json()["keys"][0]
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        payload = jwt.decode(token, key=public_key, algorithms=["RS256"])
        return payload

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        if self.FACILITY_HEADER not in request.headers:
            print("Yeah")
            return None

        external_id = request.headers[self.FACILITY_HEADER]

        try:
            UUID(external_id)
        except ValueError:
            raise InvalidToken({"detail": "Invalid Facility", "messages": []})

        facility = Facility.objects.filter(external_id=external_id).first()

        if not facility:
            raise InvalidToken({"detail": "Invalid Facility", "messages": []})

        open_id_url = "http://localhost:8090"  # TODO Replace Facility's Host name
        open_id_url += "/.well-known/openid-configuration/"

        validated_token = self.get_validated_token(open_id_url, raw_token)

        return self.get_user(validated_token), validated_token

    def get_validated_token(self, url, raw_token):
        """
        Validates an encoded JSON web token and returns a validated token
        wrapper object.
        """
        try:
            return self.open_id_authenticate(url, raw_token)
        except Exception as e:
            print(e)

        raise InvalidToken(
            {
                "detail": "Given token not valid for any token type",
                "messages": [],
            }
        )

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        if "asset_id" not in validated_token:
            raise TokenError()
        asset_external_id = validated_token["asset_id"]
        try:
            UUID(asset_external_id)
        except ValueError:
            raise InvalidToken({"detail": "Invalid Facility", "messages": []})
        # Create/Retrieve User and return them
        return None
