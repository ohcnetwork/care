from django.conf import settings
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from drf_spectacular.utils import extend_schema, extend_schema_view
from pydantic import BaseModel
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response


class ChangePasswordSpec(BaseModel):
    old_password: str
    new_password: str


@extend_schema_view(
    put=extend_schema(tags=["users"]),
    patch=extend_schema(tags=["users"]),
    request=ChangePasswordSpec,
)
class ChangePasswordView(UpdateAPIView):
    """
    API endpoint for allowing authenticated users to change their password.
    """

    def update(self, request, *args, **kwargs):
        """
        Handle password update request for the authenticated user.
        """
        data = ChangePasswordSpec(**request.data)
        if not request.user.check_password(data.old_password):
            return Response(
                {
                    "old_password": [
                        "Wrong password entered. Please check your password."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        validate_password(
            data.new_password,
            user=request.user,
            password_validators=get_password_validators(
                settings.AUTH_PASSWORD_VALIDATORS
            ),
        )

        request.user.set_password(data.new_password)
        request.user.save()
        return Response({"message": "Password updated successfully"})
