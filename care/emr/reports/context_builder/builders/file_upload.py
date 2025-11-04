from care.emr.models import Encounter
from care.emr.models.file_upload import FileUpload
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import contex_builder_registry
from care.emr.reports.context_builder.utils import format_datetime


class FileUploadContextBuilder(QuerysetContextBuilder):
    model = FileUpload

    base_filters = {
        "upload_completed": True,
        "is_archived": False,
    }
    allowed_filters = ["file_category", "file_type"]

    fields = [
        Field(
            key="file_name",
            display="File Name",
            mapping="name",
            preview_value="Chest_Xray_Report.pdf",
            description="Name of the uploaded file",
        ),
        Field(
            key="file_type",
            display="File Type",
            mapping=lambda f: f.file_type if f.file_type else "",
            preview_value="application/pdf",
            description="MIME type of the file",
        ),
        Field(
            key="file_category",
            display="Category",
            mapping=lambda f: f.file_category.replace("_", " ").title()
            if f.file_category
            else "",
            preview_value="X-Ray Image",
            description="Category of the file",
        ),
        Field(
            key="uploaded_date",
            display="Uploaded Date",
            mapping=lambda f: format_datetime(f.created_date) if f.created_date else "",
            preview_value="10/01/2024 11:45 AM",
            description="When the file was uploaded",
        ),
        Field(
            key="uploaded_by",
            display="Uploaded By",
            mapping=lambda f: f.uploaded_by.get_display_name() if f.uploaded_by else "",
            preview_value="Dr. Suresh Reddy",
            description="Person who uploaded the file",
        ),
        Field(
            key="file_size",
            display="File Size",
            mapping=lambda f: f"{round(f.meta.get('size', 0) / 1024, 2)} KB"
            if f.meta and f.meta.get("size")
            else "",
            preview_value="2.5 MB",
            description="Size of the file",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        if not encounter_id:
            raise ValueError(
                "encounter_id is required in context to build file_uploads"
            )

        try:
            encounter = Encounter.objects.get(external_id=encounter_id)
        except Encounter.DoesNotExist as e:
            msg = f"Encounter with id {encounter_id} not found"
            raise ValueError(msg) from e

        return cls.model.objects.filter(
            associating_id=str(encounter.external_id), **cls.base_filters
        )

    @classmethod
    def get_display_name(cls):
        return "File Uploads"

    @classmethod
    def get_description(cls):
        return "Documents and files uploaded for the encounter"


contex_builder_registry.register("file_uploads", FileUploadContextBuilder)
