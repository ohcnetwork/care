from django.contrib.auth.hashers import check_password
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pyotp import TOTP
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.resources.mfa.spec import LoginMethod, MFALoginRequest, MFALoginResponse
from care.emr.utils.mfa import (
    check_mfa_ip_rate_limit,
    check_mfa_user_rate_limit,
    create_auth_response,
    validate_temp_token,
)
from care.users.models import User


class MFALoginViewSet(EMRBaseViewSet):
    @extend_schema(
        description="Unified MFA login endpoint supporting TOTP and backup codes",
        request=MFALoginRequest,
        responses={200: MFALoginResponse},
    )
    @action(
        detail=False,
        methods=["POST"],
        permission_classes=[],
        authentication_classes=[],
    )
    def login(self, request):
        check_mfa_ip_rate_limit(request)
        request_data = MFALoginRequest(**request.data)

        user_id = validate_temp_token(request_data.temp_token)
        check_mfa_user_rate_limit(request, user_id)

        user = User.objects.get(external_id=user_id)

        if request_data.method == LoginMethod.totp:
            return self._handle_totp_login(user, request_data.code)
        if request_data.method == LoginMethod.backup:
            return self._handle_backup_login(user, request_data.code)

        raise ValidationError("Invalid login method")

    @staticmethod
    def _handle_totp_login(user, code):
        totp = TOTP(user.totp_secret)
        if totp.verify(code, valid_window=1):
            return create_auth_response(user)
        raise ValidationError("Invalid TOTP code")

    @staticmethod
    def _handle_backup_login(user, code):
        mfa_settings = user.mfa_settings or {}
        backup_codes = mfa_settings.get("totp", {}).get("backup_codes", [])

        matching_code = next(
            (
                code_entry
                for code_entry in backup_codes
                if not code_entry["used"] and check_password(code, code_entry["code"])
            ),
            None,
        )

        if not matching_code:
            raise ValidationError("Invalid or already used backup code")

        matching_code.update({"used": True, "used_at": timezone.now().isoformat()})
        user.mfa_settings = mfa_settings
        user.save(update_fields=["mfa_settings"])

        return create_auth_response(user)
