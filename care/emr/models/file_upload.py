import time
from uuid import uuid4

from django.db import models

from care.emr.models import EMRBaseModel
from care.emr.utils.file_manager import S3FilesManager
from care.users.models import User
from care.utils.csp.config import BucketType
from care.utils.models.validators import parse_file_extension


class FileUpload(EMRBaseModel):
    name = models.CharField(max_length=2000)
    internal_name = models.CharField(max_length=2000)
    associating_id = models.CharField(max_length=100, blank=False, null=False)
    file_type = models.CharField(max_length=100)
    file_category = models.CharField(max_length=100)
    upload_completed = models.BooleanField(default=False)

    # Archived metadata
    is_archived = models.BooleanField(default=False)
    archive_reason = models.TextField(blank=True)
    archived_datetime = models.DateTimeField(blank=True, null=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="archived_files",
    )

    files_manager = S3FilesManager(BucketType.PATIENT)

    def get_extension(self):
        extensions = parse_file_extension(self.internal_name)
        return f".{".".join(extensions)}" if extensions else ""

    def save(self, *args, **kwargs):
        """
        Create a random internal name to internally manage the file
        This is used as an intermediate step to avoid leakage of PII in-case of data leak
        """
        skip_internal_name = kwargs.pop("skip_internal_name", False)
        if (not self.internal_name or not self.id) and not skip_internal_name:
            internal_name = str(uuid4()) + str(int(time.time()))
            if self.internal_name and (extension := self.get_extension()):
                internal_name = f"{internal_name}{extension}"
            self.internal_name = internal_name
        return super().save(*args, **kwargs)
