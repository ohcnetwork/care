import time
import uuid
from uuid import uuid4

import boto3
from django.contrib.auth import get_user_model
from django.db import models

from care.utils.csp.config import BucketType, get_client_config
from care.utils.models.base import BaseManager

User = get_user_model()


class BaseFileUpload(models.Model):
    class FileCategory(models.TextChoices):
        UNSPECIFIED = "UNSPECIFIED", "UNSPECIFIED"
        XRAY = "XRAY", "XRAY"
        AUDIO = "AUDIO", "AUDIO"
        IDENTITY_PROOF = "IDENTITY_PROOF", "IDENTITY_PROOF"

    external_id = models.UUIDField(default=uuid4, unique=True, db_index=True)

    name = models.CharField(max_length=2000)  # name should not contain file extension
    internal_name = models.CharField(
        max_length=2000
    )  # internal_name should include file extension
    associating_id = models.CharField(max_length=100, blank=False, null=False)
    file_type = models.IntegerField(default=0)
    file_category = models.CharField(
        choices=FileCategory,
        default=FileCategory.UNSPECIFIED,
        max_length=100,
    )
    created_date = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, db_index=True
    )
    modified_date = models.DateTimeField(
        auto_now=True, null=True, blank=True, db_index=True
    )
    upload_completed = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False, db_index=True)

    objects = BaseManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if "force_insert" in kwargs or (not self.internal_name):
            internal_name = str(uuid4()) + str(int(time.time()))
            if self.internal_name:
                parts = self.internal_name.split(".")
                if len(parts) > 1:
                    internal_name = f"{internal_name}.{parts[-1]}"
            self.internal_name = internal_name
        return super().save(*args, **kwargs)

    def delete(self, *args):
        self.deleted = True
        self.save(update_fields=["deleted"])

    def get_extension(self):
        parts = self.internal_name.split(".")
        return f".{parts[-1]}" if len(parts) > 1 else ""

    def signed_url(
        self, duration=60 * 60, mime_type=None, bucket_type=BucketType.PATIENT
    ):
        config, bucket_name = get_client_config(bucket_type, external=True)
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
        config, bucket_name = get_client_config(bucket_type, external=True)
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


class FileUpload(BaseFileUpload):
    """
    Stores data about all file uploads
    the file can belong to any type ie Patient , Consultation , Daily Round and so on ...
    the file will be uploaded to the corresponding folders
    the file name will be randomised and converted into an internal name before storing in S3
    all data will be private and file access will be given on a NEED TO BASIS ONLY
    """

    class FileType(models.IntegerChoices):
        OTHER = 0, "OTHER"
        PATIENT = 1, "PATIENT"
        CONSULTATION = 2, "CONSULTATION"
        SAMPLE_MANAGEMENT = 3, "SAMPLE_MANAGEMENT"
        CLAIM = 4, "CLAIM"
        DISCHARGE_SUMMARY = 5, "DISCHARGE_SUMMARY"
        COMMUNICATION = 6, "COMMUNICATION"
        CONSENT_RECORD = 7, "CONSENT_RECORD"
        ABDM_HEALTH_INFORMATION = 8, "ABDM_HEALTH_INFORMATION"

    file_type = models.IntegerField(choices=FileType, default=FileType.PATIENT)
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

    # TODO: switch to Choices.choices
    FileTypeChoices = [(x.value, x.name) for x in FileType]
    FileCategoryChoices = [(x.value, x.name) for x in BaseFileUpload.FileCategory]

    def __str__(self):
        return f"{self.FileTypeChoices[self.file_type][1]} - {self.name}{' (Archived)' if self.is_archived else ''}"

    def save(self, *args, **kwargs):
        from care.facility.models import PatientConsent

        if self.file_type == self.FileType.CONSENT_RECORD:
            new_consent = False
            if not self.pk and not self.is_archived:
                new_consent = True
            consent = PatientConsent.objects.filter(
                external_id=uuid.UUID(self.associating_id), archived=False
            ).first()
            consultation = consent.consultation
            consent_types = (
                PatientConsent.objects.filter(consultation=consultation, archived=False)
                .annotate(
                    str_external_id=models.functions.Cast(
                        "external_id", models.CharField()
                    )
                )
                .annotate(
                    has_files=(
                        models.Exists(
                            FileUpload.objects.filter(
                                associating_id=models.OuterRef("str_external_id"),
                                file_type=self.FileType.CONSENT_RECORD,
                                is_archived=False,
                            ).exclude(pk=self.pk if self.is_archived else None)
                        )
                        if not new_consent
                        else models.Value(value=True)
                    )
                )
                .filter(has_files=True)
                .distinct("type")
                .values_list("type", flat=True)
            )
            consultation.has_consents = list(consent_types)
            consultation.save()

        return super().save(*args, **kwargs)
