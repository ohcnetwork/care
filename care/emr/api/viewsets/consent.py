import logging

from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.api.viewsets.file_upload import file_authorizer
from care.emr.models import Encounter, FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.consent.spec import (
    ConsentCreateSpec,
    ConsentListSpec,
    ConsentRetrieveSpec,
    ConsentUpdateSpec,
    ConsentVerificationSpec,
)
from care.emr.resources.file_upload.spec import (
    ConsentFileUploadCreateSpec,
    FileUploadRetrieveSpec,
)
from care.security.authorization import AuthorizationController

logger = logging.getLogger(__name__)


class ConsentViewSet(EMRModelViewSet, EncounterBasedAuthorizationBase):
    database_model = Consent
    pydantic_model = ConsentCreateSpec
    pydantic_read_model = ConsentListSpec
    pydantic_update_model = ConsentUpdateSpec
    pydantic_retrieve_model = ConsentRetrieveSpec

    def get_patient_obj(self):
        return self.get_object().encounter.patient

    def authorize_read_encounter(self):
        if not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, self.get_patient_obj()
        ):
            if encounter := self.request.GET.get("encounter"):
                encounter_obj = get_object_or_404(Encounter, external_id=encounter)
                if not AuthorizationController.call(
                    "can_view_encounter_obj", self.request.user, encounter_obj
                ):
                    raise PermissionDenied("Permission denied to user")
            else:
                raise PermissionDenied("Permission denied to user")

    def get_queryset(self):
        # Todo: Implement File authorization so that only attachments that the user has access to are returned
        if self.action == "list":
            # Todo: Implement permission checks for encounters to return only consent's whose encounters the user has access to
            pass
        elif not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, self.get_patient_obj()
        ):
            if encounter := self.get_object().encounter:
                encounter_obj = get_object_or_404(
                    Encounter, external_id=encounter.external_id
                )
                if not AuthorizationController.call(
                    "can_view_encounter_obj", self.request.user, encounter_obj
                ):
                    raise PermissionDenied("Permission denied to user")
            else:
                raise PermissionDenied("Permission denied to user")

        return super().get_queryset()

    @action(detail=True, methods=["GET"])
    def get_attachments(self, request, *args, **kwargs):
        instance = self.get_object()
        attachments = [
            FileUploadRetrieveSpec.serialize(
                FileUpload.objects.get(external_id=attachment)
            ).to_json()
            for attachment in instance.source_attachment or []
        ]
        return Response(attachments)

    @extend_schema(request=ConsentFileUploadCreateSpec)
    @action(detail=True, methods=["POST"])
    def add_attachment(self, request, *args, **kwargs):
        instance = self.get_object()
        request.data["associating_id"] = instance.external_id
        file_obj = ConsentFileUploadCreateSpec(**request.data).de_serialize()
        file_authorizer(
            request.user,
            file_obj.file_type,
            file_obj.associating_id,
            "write",
        )
        file_obj.created_by = self.request.user
        file_obj.updated_by = self.request.user
        file_obj.save()
        instance.source_attachment.append(file_obj.external_id)
        instance.save(update_fields=["source_attachment"])
        serialized = ConsentRetrieveSpec.serialize(instance).to_json()
        return Response(serialized)

    class AttachmentRemovalSchema(BaseModel):
        attachment_id: UUID4

    @extend_schema(request=AttachmentRemovalSchema)
    @action(detail=True, methods=["POST"])
    def remove_attachment(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = self.AttachmentRemovalSchema(**request.data)
        if request_data.attachment_id not in instance.source_attachment:
            raise ValidationError("Attachment not associated with the consent")
        attachment = get_object_or_404(
            FileUpload, external_id=request_data.attachment_id
        )
        file_authorizer(
            request.user,
            attachment.file_type,
            attachment.associating_id,
            "write",
        )
        instance.source_attachment.remove(request_data.attachment_id)
        instance.save(update_fields=["source_attachment"])
        serialized = ConsentRetrieveSpec.serialize(instance).to_json()
        return Response(serialized)

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

    @action(detail=True, methods=["GET"])
    def get_verification_details(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(instance.verification_details)
