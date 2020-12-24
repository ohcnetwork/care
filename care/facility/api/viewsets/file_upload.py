import base64
from typing import List

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django_filters import rest_framework as filters
from rest_framework import request
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.file_upload import (
    FileUploadCreateSerializer,
    FileUploadListSerializer,
    FileUploadRetrieveSerializer,
    check_permissions,
)
from care.facility.models.file_upload import FileUpload


class FileUploadViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet,
):
    queryset = (
        FileUpload.objects.all().select_related("uploaded_by").order_by("-created_date")
    )
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"

    def get_serializer_class(self):
        if self.action == "create":
            return FileUploadCreateSerializer
        elif self.action == "list":
            return FileUploadListSerializer
        elif self.action == "retrieve":
            return FileUploadRetrieveSerializer
        else:
            raise Exception()

    def get_queryset(self):
        if (
            "file_type" not in self.request.GET
            or "associating_id" not in self.request.GET
        ):
            raise ValidationError("Bad Request")
        file_type = self.request.GET["file_type"]
        associating_id = self.request.GET["associating_id"]
        if file_type not in FileUpload.FileType.__members__:
            raise ValidationError("Bad Request")
        file_type = FileUpload.FileType[file_type].value
        associating_internal_id = check_permissions(
            file_type, associating_id, self.request.user
        )
        return self.queryset.filter(
            file_type=file_type, associating_id=associating_internal_id
        )
