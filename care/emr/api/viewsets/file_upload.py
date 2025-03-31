import base64

import magic
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models import Encounter, FileUpload, Patient
from care.emr.models.consent import Consent
from care.emr.resources.file_upload.spec import (
    FileTypeChoices,
    FileUploadCreateSpec,
    FileUploadListSpec,
    FileUploadRetrieveSpec,
    FileUploadUpdateSpec,
)
from care.security.authorization import AuthorizationController


def file_authorizer(user, file_type, associating_id, permission):
    allowed = False
    if file_type == FileTypeChoices.patient.value:
        patient_obj = get_object_or_404(Patient, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, patient_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_write_patient_obj", user, patient_obj
            )
    elif file_type == FileTypeChoices.encounter.value:
        encounter_obj = get_object_or_404(Encounter, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, encounter_obj.patient
            ) or AuthorizationController.call(
                "can_view_encounter_obj", user, encounter_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_update_encounter_obj", user, encounter_obj
            )
    elif file_type == FileTypeChoices.consent.value:
        encounter_obj = get_object_or_404(Consent, external_id=associating_id).encounter
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, encounter_obj.patient
            ) or AuthorizationController.call(
                "can_view_encounter_obj", user, encounter_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_update_encounter_obj", user, encounter_obj
            )

    if not allowed:
        raise PermissionDenied("Cannot View File")


class FileCategoryFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value:
            return qs.filter(file_category__in=value.split(","))
        return qs


class FileUploadFilter(filters.FilterSet):
    is_archived = filters.BooleanFilter(field_name="is_archived")
    file_category = FileCategoryFilter()
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class FileUploadViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = FileUpload
    pydantic_model = FileUploadCreateSpec
    pydantic_retrieve_model = FileUploadRetrieveSpec
    pydantic_update_model = FileUploadUpdateSpec
    pydantic_read_model = FileUploadListSpec
    filterset_class = FileUploadFilter
    filter_backends = [filters.DjangoFilterBackend]

    def authorize_create(self, instance):
        file_authorizer(
            self.request.user,
            instance.file_type,
            instance.associating_id,
            "write",
        )

    def authorize_update(self, request_obj, model_instance):
        file_authorizer(
            self.request.user,
            model_instance.file_type,
            model_instance.associating_id,
            "write",
        )

    def get_queryset(self):
        if self.action == "list":
            if (
                "file_type" not in self.request.GET
                and "associating_id" not in self.request.GET
            ):
                raise PermissionError("Cannot filter files")
            file_authorizer(
                self.request.user,
                self.request.GET.get("file_type"),
                self.request.GET.get("associating_id"),
                "read",
            )
            return (
                super()
                .get_queryset()
                .filter(
                    file_type=self.request.GET.get("file_type"),
                    associating_id=self.request.GET.get("associating_id"),
                    upload_completed=True,
                )
            )
        obj = get_object_or_404(FileUpload, external_id=self.kwargs["external_id"])
        file_authorizer(self.request.user, obj.file_type, obj.associating_id, "read")
        return super().get_queryset()

    @extend_schema(responses={200: FileUploadListSpec})
    @action(detail=True, methods=["POST"])
    def mark_upload_completed(self, request, *args, **kwargs):
        obj = self.get_object()
        file_authorizer(request.user, obj.file_type, obj.associating_id, "write")
        obj.upload_completed = True
        obj.save(update_fields=["upload_completed"])
        return Response(FileUploadListSpec.serialize(obj).to_json())

    class ArchiveRequestSpec(BaseModel):
        archive_reason: str

    @extend_schema(
        request=ArchiveRequestSpec,
        responses={200: FileUploadListSpec},
    )
    @action(detail=True, methods=["POST"])
    def archive(self, request, *args, **kwargs):
        obj = self.get_object()
        request_data = self.ArchiveRequestSpec(**request.data)
        file_authorizer(request.user, obj.file_type, obj.associating_id, "write")
        obj.is_archived = True
        obj.archive_reason = request_data.archive_reason
        obj.archived_datetime = timezone.now()
        obj.archived_by = request.user
        obj.save(
            update_fields=[
                "is_archived",
                "archive_reason",
                "archived_datetime",
                "archived_by",
            ]
        )
        return Response(FileUploadListSpec.serialize(obj).to_json())

    @action(detail=False, methods=["POST"], url_path="upload-file")
    def upload_file(self, request, *args, **kwargs):
        file_name = request.data.get("original_name")
        file_data = request.data.get("file_data")

        if not file_name or not file_data:
            raise ValidationError(
                "Missing required fields: 'original_name' or 'file_data'"
            )

        try:
            file_content = base64.b64decode(file_data)
        except Exception as e:
            error = "Invalid base64-encoded file data"
            raise ValidationError(error) from e

        uploaded_file = ContentFile(file_content, name=file_name)

        max_file_size = settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024
        if uploaded_file.size > max_file_size:
            error = f"File size exceeds the limit of {max_file_size / (1024 * 1024)}MB"
            raise ValidationError(error)

        try:
            mime_type = magic.from_buffer(file_content[:2048], mime=True)
        except Exception as e:
            error = "Error detecting file type."
            raise ValidationError(error) from e

        if mime_type not in settings.ALLOWED_MIME_TYPES:
            error = f"File type '{mime_type}' is not allowed"
            raise ValidationError(error)

        request_data = {
            "original_name": file_name,
            "name": request.data.get("name"),
            "associating_id": request.data.get("associating_id"),
            "file_type": request.data.get("file_type"),
            "file_category": request.data.get("file_category"),
            "mime_type": mime_type,
        }

        with transaction.atomic():
            file_upload = FileUploadCreateSpec(**request_data).de_serialize()
            file_upload._just_created = False  # noqa SLF001
            self.authorize_create(file_upload)
            file_upload.save()

            try:
                file_upload.files_manager.put_object(file_upload, uploaded_file)
                file_upload.upload_completed = True
                file_upload.save(skip_internal_name=True)
            except Exception as e:
                error_msg = "Failed to upload file to storage"
                raise ValidationError(error_msg) from e

        return Response(FileUploadRetrieveSpec.serialize(file_upload).to_json())
