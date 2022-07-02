from django.utils.translation import ugettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from config.patient_otp_token import PatientToken


class PatientOtpObject:
    service = "patient_otp"
    is_alternative_login = True
    is_authenticated = True
    is_anonymous = True
    phone_number = None


class CustomJWTAuthentication(JWTAuthentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header.
    """

    www_authenticate_realm = "api"

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token

    def get_validated_token(self, raw_token):
        """
        Validates an encoded JSON web token and returns a validated token
        wrapper object.
        """
        messages = []
        try:
            return PatientToken(raw_token)
        except TokenError as e:
            messages.append(
                {"token_class": PatientToken.__name__, "token_type": PatientToken.token_type, "message": e.args[0]}
            )

        raise InvalidToken(
            {"detail": _("Given token not valid for any token type"), "messages": messages,}
        )


class JWTTokenPatientAuthentication(CustomJWTAuthentication):
    def get_user(self, validated_token):
        """
        Returns a stateless user object which is backed by the given validated
        token.
        """
        obj = PatientOtpObject()
        obj.phone_number = validated_token["phone_number"]
        return obj
