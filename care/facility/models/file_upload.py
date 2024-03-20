import enum
import time
from uuid import uuid4

import boto3
from django.db import models

from care.facility.models import FacilityBaseModel
from care.users.models import User
from care.utils.csp.config import BucketType, get_client_config


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
        SAMPLE_MANAGEMENT = 3
        CLAIM = 4
        DISCHARGE_SUMMARY = 5
        COMMUNICATION = 6

    class FileCategory(enum.Enum):
        UNSPECIFIED = "UNSPECIFIED"
        XRAY = "XRAY"
        AUDIO = "AUDIO"
        IDENTITY_PROOF = "IDENTITY_PROOF"

    FileTypeChoices = [(e.value, e.name) for e in FileType]
    FileCategoryChoices = [(e.value, e.name) for e in FileCategory]

    name = models.CharField(max_length=2000)  # name should not contain file extension
    internal_name = models.CharField(
        max_length=2000
    )  # internal_name should include file extension
    associating_id = models.CharField(max_length=100, blank=False, null=False)
    upload_completed = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archive_reason = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="uploaded_by",
    )
    archived_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="archived_by",
    )
    archived_datetime = models.DateTimeField(blank=True, null=True)
    file_type = models.IntegerField(
        choices=FileTypeChoices, default=FileType.PATIENT.value
    )
    file_category = models.CharField(
        choices=FileCategoryChoices,
        default=FileCategory.UNSPECIFIED.value,
        max_length=100,
    )

    def get_extension(self):
        parts = self.internal_name.split(".")
        return f".{parts[-1]}" if len(parts) > 1 else ""

    def save(self, *args, **kwargs):
        if "force_insert" in kwargs or (not self.internal_name):
            internal_name = str(uuid4()) + str(int(time.time()))
            if self.internal_name:
                parts = self.internal_name.split(".")
                if len(parts) > 1:
                    internal_name = f"{internal_name}.{parts[-1]}"
            self.internal_name = internal_name
        return super().save(*args, **kwargs)

    def signed_url(
        self, duration=60 * 60, mime_type=None, bucket_type=BucketType.PATIENT
    ):
        config, bucket_name = get_client_config(bucket_type, True)
        s3 = boto3.client("s3", **config)
        params = {
            "Bucket": bucket_name,
            "Key": f"{self.FileType(self.file_type).name}/{self.internal_name}",
        }
        if mime_type:
            params["ContentType"] = mime_type
        return s3.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=duration,  # seconds
        )

    def read_signed_url(self, duration=60 * 60, bucket_type=BucketType.PATIENT):
        config, bucket_name = get_client_config(bucket_type, True)
        s3 = boto3.client("s3", **config)
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": f"{self.FileType(self.file_type).name}/{self.internal_name}",
            },
            ExpiresIn=duration,  # seconds
        )

    def put_object(self, file, bucket_type=BucketType.PATIENT, **kwargs):
        config, bucket_name = get_client_config(bucket_type)
        s3 = boto3.client("s3", **config)
        return s3.put_object(
            Body=file,
            Bucket=bucket_name,
            Key=f"{self.FileType(self.file_type).name}/{self.internal_name}",
            **kwargs,
        )

    def get_object(self, bucket_type=BucketType.PATIENT, **kwargs):
        config, bucket_name = get_client_config(bucket_type)
        s3 = boto3.client("s3", **config)
        return s3.get_object(
            Bucket=bucket_name,
            Key=f"{self.FileType(self.file_type).name}/{self.internal_name}",
            **kwargs,
        )

    def file_contents(self):
        response = self.get_object()
        content_type = response["ContentType"]
        content = response["Body"].read()
        return content_type, content
