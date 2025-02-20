from django.contrib.auth.hashers import check_password
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.api.viewsets.totp import MFALoginRequest, MFALoginResponse
from care.emr.utils.mfa import (
    check_mfa_ip_rate_limit,
    check_mfa_user_rate_limit,
    create_auth_response,
    validate_temp_token,
)
from care.users.models import User


class BackupLoginViewSet(EMRBaseViewSet):
    @extend_schema(
        description="Login using a backup code",
        request=MFALoginRequest,
        responses={
            200: MFALoginResponse,
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        permission_classes=[],
        authentication_classes=[],
    )
    def backup_login(self, request):
        check_mfa_ip_rate_limit(request)
        request_data = MFALoginRequest(**request.data)

        user_id = validate_temp_token(request_data.temp_token)
        check_mfa_user_rate_limit(request, user_id)

        user = User.objects.get(external_id=user_id)
        mfa_settings = user.mfa_settings or {}
        backup_codes = mfa_settings.get("totp", {}).get("backup_codes", [])

        matching_code = next(
            (
                code
                for code in backup_codes
                if not code["used"] and check_password(request_data.code, code["code"])
            ),
            None,
        )

        if not matching_code:
            return Response(
                {"error": "Invalid or already used backup code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        matching_code.update({"used": True, "used_at": timezone.now().isoformat()})
        user.mfa_settings = mfa_settings
        user.save(update_fields=["mfa_settings"])

        return create_auth_response(user)
