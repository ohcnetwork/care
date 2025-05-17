from care.emr.models import FileUpload
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection

FILE_CATEGORY_DISPLAY = {
    "audio": "Audio File",
    "xray": "X-Ray Image",
    "identity_proof": "Identity Proof",
    "unspecified": "Unspecified",
    "discharge_summary": "Discharge Summary",
    "consent_attachment": "Consent Form/Attachment",
}


class FileSection(BaseSection):
    __model__ = FileUpload

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

        self.register_field("name", lambda o: o.name)
        self.register_field("type", lambda o: o.file_type)
        self.register_field(
            "category", lambda o: FILE_CATEGORY_DISPLAY.get(o.file_category)
        )

    def fetch_data(self):
        return FileUpload.objects.filter(
            associating_id=self.context["encounter"].external_id,
            upload_completed=True,
            is_archived=False,
        )


SectionRegistry.register("file_upload", FileSection)
