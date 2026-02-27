from django_filters import rest_framework as filters

from care.emr.api.viewsets.file_upload import FileCategoryFilter
from care.emr.models.file_upload import FileUpload
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


class FileUploadReportFilter(filters.FilterSet):
    file_category = FileCategoryFilter()
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class FileUploadContextBuilder(QuerysetContextBuilder):
    filterset_class = FileUploadReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    name = Field(
        display="Filename",
        preview_value="lab_report.pdf",
        description="Name of the uploaded file",
    )

    url = Field(
        display="File URL",
        preview_value="https://s3.amazonaws.com/bucket/patient/12345/file.pdf",
        mapping=lambda f: f.files_manager.read_signed_url(f)
        if f.upload_completed
        else None,
        description="URL to access the uploaded file",
    )

    def get_context(self):
        return FileUpload.objects.filter(
            associating_id=self.parent_context.external_id, is_archived=False
        )
