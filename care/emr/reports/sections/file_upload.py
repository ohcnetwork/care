from care.emr.models import FileUpload
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class FileSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

    def fetch_data(self):
        return FileUpload.objects.filter(
            associating_id=self.context["encounter"].external_id,
            upload_completed=True,
            is_archived=False,
        )


SectionRegistry.register("file_upload", FileSection)
