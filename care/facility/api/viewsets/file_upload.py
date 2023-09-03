from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.file_upload import (
    FileUploadCreateSerializer,
    FileUploadListSerializer,
    FileUploadRetrieveSerializer,
    FileUploadUpdateSerializer,
    check_permissions,
)
from care.facility.models.file_upload import FileUpload


class FileUploadFilter(filters.FilterSet):
    file_category = filters.CharFilter(field_name="file_category")
    is_archived = filters.BooleanFilter(field_name="is_archived")


class FileUploadViewSet(
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    queryset = (
        FileUpload.objects.all().select_related("uploaded_by").order_by("-created_date")
    )
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FileUploadFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return FileUploadRetrieveSerializer
        if self.action == "list":
            return FileUploadListSerializer
        if self.action == "create":
            return FileUploadCreateSerializer
        return FileUploadUpdateSerializer

    def get_queryset(self):
        if "file_type" not in self.request.GET:
            raise ValidationError({"file_type": "file_type missing in request params"})
        if "associating_id" not in self.request.GET:
            raise ValidationError(
                {"associating_id": "associating_id missing in request params"},
            )
        file_type = self.request.GET["file_type"]
        associating_id = self.request.GET["associating_id"]
        if file_type not in FileUpload.FileType.__members__:
            raise ValidationError({"file_type": "invalid file type"})
        file_type = FileUpload.FileType[file_type].value
        associating_internal_id = check_permissions(
            file_type,
            associating_id,
            self.request.user,
            "read",
        )
        return self.queryset.filter(
            file_type=file_type,
            associating_id=associating_internal_id,
        )
