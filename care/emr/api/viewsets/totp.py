from contextlib import contextmanager
from functools import partial
from secrets import choice
from string import digits

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pyotp import TOTP, random_base32
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import Token

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.resources.mfa.spec import (
    PasswordVerifyRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPVerifyResponse,
)
from care.emr.tasks.totp import send_totp_disabled_email, send_totp_enabled_email
from care.emr.utils.mfa import verify_password
from care.users.locks import lock_user_auth
from config.authentication import CustomJWTAuthentication


class TOTPViewSet(EMRBaseViewSet):
    @staticmethod
    @contextmanager
    def _lock_user(request):
        with lock_user_auth(request.user.external_id):
            if isinstance(request.auth, Token):
                user = CustomJWTAuthentication().get_user(request.auth)
            else:
                request.user.refresh_from_db()
                user = request.user
            yield user

    @extend_schema(
        description="Initialize TOTP setup for user",
        responses={
            200: TOTPSetupResponse,
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(detail=False, methods=["POST"])
    def setup(self, request):
        password = PasswordVerifyRequest(**request.data).password
        with self._lock_user(request) as user:
            verify_password(user, password)

            self._validate_totp_state(user, required_state=False)

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
        request_data = TOTPVerifyRequest(**request.data)
        with self._lock_user(request) as user:
            if not user.totp_secret:
                raise ValidationError("TOTP not configured for your account")

            mfa_settings = user.mfa_settings or {}

            self._validate_totp_state(user, required_state=False)

            secret = user.totp_secret
            totp = TOTP(secret)

            if not totp.verify(request_data.code, valid_window=1):
                return Response(
                    {"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST
                )

            backup_codes = self._generate_backup_codes()

            mfa_settings["totp"] = {
                "enabled": True,
                "enabled_at": timezone.now().isoformat(),
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

        transaction.on_commit(
            partial(send_totp_enabled_email.delay, user.email, user.username)
        )
        response_data = TOTPVerifyResponse(backup_codes=backup_codes)
        return Response(response_data.model_dump())

    @extend_schema(
        description="Disable TOTP-based two-factor authentication",
        request=PasswordVerifyRequest,
        responses={
            200: {},
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(detail=False, methods=["POST"])
    def disable(self, request):
        password = PasswordVerifyRequest(**request.data).password
        with self._lock_user(request) as user:
            verify_password(user, password)

            mfa_settings = user.mfa_settings or {}

            self._validate_totp_state(user, required_state=True)

            mfa_settings["totp"] = {
                "enabled": False,
                "totp_disabled_at": timezone.now().isoformat(),
                "backup_codes": [],
            }
            user.mfa_settings = mfa_settings
            user.totp_secret = None
            user.save(update_fields=["mfa_settings", "totp_secret"])

        transaction.on_commit(
            partial(send_totp_disabled_email.delay, user.email, user.username)
        )

        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        description="Regenerate TOTP backup codes",
        request=PasswordVerifyRequest,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "backup_codes": {"type": "array", "items": {"type": "string"}}
                },
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(detail=False, methods=["POST"])
    def regenerate_backup_codes(self, request):
        password = PasswordVerifyRequest(**request.data).password
        with self._lock_user(request) as user:
            verify_password(user, password)

            mfa_settings = user.mfa_settings or {}

            self._validate_totp_state(user, required_state=True)

            backup_codes = self._generate_backup_codes()
            mfa_settings["totp"]["backup_codes"] = [
                {
                    "code": make_password(code),
                    "used": False,
                    "created_at": timezone.now().isoformat(),
                }
                for code in backup_codes
            ]
            user.mfa_settings = mfa_settings
            user.save(update_fields=["mfa_settings"])

        return Response({"backup_codes": backup_codes})

    @staticmethod
    def _validate_totp_state(user, required_state: bool):
        is_enabled = user.is_mfa_enabled()

        if required_state and not is_enabled:
            raise ValidationError(
                "Two-factor authentication is not enabled for your account"
            )

        if not required_state and is_enabled:
            raise ValidationError(
                "Two-factor authentication is already enabled for your account"
            )
