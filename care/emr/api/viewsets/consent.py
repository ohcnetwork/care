from django.db import transaction
from pydantic import BaseModel, ValidationError
from pydantic.v1 import UUID4
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.file_upload import file_authorizer
from care.emr.models import FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.consent.spec import (
    ConsentCreateSpec,
    ConsentListSpec,
    ConsentRetrieveSpec,
    ConsentUpdateSpec,
)
from care.emr.resources.file_upload.spec import FileUploadCreateSpec


class ConsentViewSet(EMRModelViewSet):
    database_model = Consent
    pydantic_model = ConsentCreateSpec
    pydantic_read_model = ConsentListSpec
    pydantic_update_model = ConsentUpdateSpec
    pydantic_retrieve_model = ConsentRetrieveSpec

    def perform_create(self, instance):
        with transaction.atomic():
            attachment_ids = []
            attachments = instance.pop("source_attachment", [])
            for attachment in attachments:
                file_authorizer(
                    self.request.user,
                    attachment.file_type,
                    attachment.associating_id,
                    "write",
                )
                file = FileUpload.objects.create(attachment)
                attachment_ids.append(file.external_id)
            instance["source_attachment"] = attachment_ids
            super().perform_create(instance)

    class AttachmentAdditionSchema(BaseModel):
        source_attachment: FileUploadCreateSpec

    @action(detail=True, methods=["POST"])
    def add_attachment(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = self.AttachmentAdditionSchema(**request.data)
        file_authorizer(
            request.user,
            request_data.source_attachment.file_type,
            request_data.source_attachment.associating_id,
            "write",
        )
        file = FileUpload.objects.create(request_data.source_attachment)
        instance.source_attachment.append(file.external_id)
        instance.save(update_fields=["source_attachment"])
        return Response(ConsentRetrieveSpec.serialize(instance).to_json())

    class AttachmentRemovalSchema(BaseModel):
        attachment_id: UUID4

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
        return Response(ConsentRetrieveSpec.serialize(instance).to_json())
