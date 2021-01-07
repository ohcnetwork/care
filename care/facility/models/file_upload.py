import enum
import time
import boto3
from uuid import uuid4
from django.conf import settings
from django.db import models

from care.facility.models import FacilityBaseModel
from care.users.models import User


class FileUpload(FacilityBaseModel):
    """
    Stores data about all file uploads
    the file can belong to any type ie Patient , Consultation , Daily Round and so on ...
    the file will be uploaded to the corresponding folders
    the file name will be randomised and converted into an internal name before storing in S3
    all data will be private and file access will be given on a NEED TO BASIS ONLY
    """

    # TODO : Periodic tasks that removes files that were never uploaded

    class FileType(enum.Enum):
        PATIENT = 1
        CONSULTATION = 2

    FileTypeChoices = [(e.value, e.name) for e in FileType]

    name = models.CharField(max_length=2000)
    internal_name = models.CharField(max_length=2000)
    associating_id = models.CharField(max_length=100, blank=False, null=False)
    upload_completed = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True
    )
    file_type = models.IntegerField(
        choices=FileTypeChoices, default=FileType.PATIENT.value
    )

    def save(self, *args, **kwargs):
        if "force_insert" in kwargs or (not self.internal_name):
            internal_name = str(uuid4()) + str(int(time.time()))
            if self.internal_name:
                parts = self.internal_name.split(".")
                if len(parts) > 1:
                    internal_name = internal_name + "." + parts[-1]
            self.internal_name = internal_name
            return super().save(*args, **kwargs)

    def signed_url(self):
        s3Client = boto3.client(
            "s3",
            region_name="ap-south-1",
            aws_access_key_id=settings.FILE_UPLOAD_KEY,
            aws_secret_access_key=settings.FILE_UPLOAD_SECRET,
        )
        signed_url = s3Client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.FILE_UPLOAD_BUCKET,
                "Key": self.FileType(self.file_type).name + "/" + self.internal_name,
            },
            ExpiresIn=60 * 60,  # One Hour
        )
        return signed_url

    def read_signed_url(self):
        s3Client = boto3.client(
            "s3",
            region_name="ap-south-1",
            aws_access_key_id=settings.FILE_UPLOAD_KEY,
            aws_secret_access_key=settings.FILE_UPLOAD_SECRET,
        )
        signed_url = s3Client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.FILE_UPLOAD_BUCKET,
                "Key": self.FileType(self.file_type).name + "/" + self.internal_name,
            },
            ExpiresIn=60 * 60,  # One Hour
        )
        return signed_url
