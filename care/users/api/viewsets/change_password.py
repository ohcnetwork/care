from django.conf import settings
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from pydantic import BaseModel, ValidationInfo, field_validator, model_validator
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response

from care.emr.api.viewsets.base import emr_exception_handler


class ChangePasswordSpec(BaseModel):
    old_password: str
    new_password: str

    @field_validator("old_password", "new_password", mode="before")
    @classmethod
    def strip_passwords(cls, v):
        """Strip leading and trailing whitespace from passwords."""
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_passwords(self, info: ValidationInfo):
        user = info.context.get("user")
        if not user.check_password(self.old_password):
            msg = "Wrong password entered. Please check your password."
            raise ValueError(msg)

        try:
            validate_password(
                self.new_password,
                user=user,
                password_validators=get_password_validators(
                    settings.AUTH_PASSWORD_VALIDATORS
                ),
            )
        except DjangoValidationError as e:
            raise ValueError(", ".join(e.messages)) from e
        return self


@extend_schema_view(
    put=extend_schema(tags=["users"], request=ChangePasswordSpec),
    patch=extend_schema(tags=["users"], request=ChangePasswordSpec),
)
class ChangePasswordView(UpdateAPIView):
    """
    API endpoint for allowing authenticated users to change their password.
    """

    def get_exception_handler(self):
        return emr_exception_handler

    def update(self, request, *args, **kwargs):
        """
        Handle password update request for the authenticated user.
        """
        data = ChangePasswordSpec.model_validate(
            request.data, context={"user": request.user}
        )

        request.user.set_password(data.new_password)
        request.user.save()
        return Response({"message": "Password updated successfully"})
