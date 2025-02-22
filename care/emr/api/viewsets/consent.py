from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.consent import Consent
from care.emr.resources.consent.spec import (
    ConsentCreateSpec,
    ConsentListSpec,
    ConsentRetrieveSpec,
    ConsentUpdateSpec,
    ConsentVerificationSpec,
)


class ConsentViewSet(EMRModelViewSet, EncounterBasedAuthorizationBase):
    database_model = Consent
    pydantic_model = ConsentCreateSpec
    pydantic_read_model = ConsentListSpec
    pydantic_update_model = ConsentUpdateSpec
    pydantic_retrieve_model = ConsentRetrieveSpec

    def get_queryset(self):
        self.authorize_read_encounter()
        return (
            super()
            .get_queryset()
            .select_related("encounter", "created_by", "updated_by")
        )

    @extend_schema(request=ConsentVerificationSpec)
    @action(detail=True, methods=["POST"])
    def add_verification(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = ConsentVerificationSpec(**request.data)
        request_data.verification.verified_by = self.request.user.external_id

        if request_data.verified_by in [
            verification.verified_by for verification in instance.verification_details
        ]:
            raise ValidationError("Consent is already verified by the user")

        request_data.verification.verification_date = now()
        instance.verification_details.append(request_data.verification)
        instance.save(update_fields=["verification_details"])
        serialized = ConsentRetrieveSpec.serialize(instance).to_json()
        return Response(serialized)

    class VerificationRemovalSchema(BaseModel):
        verified_by: UUID4 | None = None

    @extend_schema(request=VerificationRemovalSchema)
    @action(detail=True, methods=["POST"])
    def remove_verification(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = self.VerificationRemovalSchema(**request.data)

        match = None
        for verification in instance.verification_details:
            if str(verification.get("verified_by")) == str(request_data.verified_by):
                match = verification
                break

        if not match:
            raise ValidationError("Consent is not verified by the user")

        instance.verification_details.remove(match)
        instance.save(update_fields=["verification_details"])

        serialized = ConsentRetrieveSpec.serialize(instance).to_json()
        return Response(serialized)
