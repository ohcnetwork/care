import enum
from typing import TypedDict

from django.conf import settings


class ClientConfig(TypedDict):
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    endpoint_url: str


type BucketName = str


class CSProvider(enum.Enum):
    AWS = "AWS"
    AWS_ROLE_BASED = "AWS_ROLE_BASED"
    GCP = "GCP"
    DIGITAL_OCEAN = "DIGITAL_OCEAN"
    MINIO = "MINIO"
    DOCKER = "DOCKER"  # localstack in docker
    LOCAL = "LOCAL"  # localstack on host


class BucketType(enum.Enum):
    PATIENT = "PATIENT"
    FACILITY = "FACILITY"
    REPORT = "REPORT"


def get_facility_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    params = {"region_name": settings.FACILITY_S3_REGION}
    if CSProvider.AWS_ROLE_BASED.value != settings.BUCKET_PROVIDER:
        params["aws_access_key_id"] = settings.FACILITY_S3_KEY
        params["aws_secret_access_key"] = settings.FACILITY_S3_SECRET
        params["endpoint_url"] = (
            settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT
            if external
            else settings.FACILITY_S3_BUCKET_ENDPOINT
        )
    return params, settings.FACILITY_S3_BUCKET


def get_patient_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    params = {"region_name": settings.FACILITY_S3_REGION}
    if CSProvider.AWS_ROLE_BASED.value != settings.BUCKET_PROVIDER:
        params["aws_access_key_id"] = settings.FACILITY_S3_KEY
        params["aws_secret_access_key"] = settings.FACILITY_S3_SECRET
        params["endpoint_url"] = (
            settings.FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT
            if external
            else settings.FILE_UPLOAD_BUCKET_ENDPOINT
        )
    return params, settings.FILE_UPLOAD_BUCKET


def get_report_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    """Get bucket configuration for reports - uses same bucket as patient files"""
    params = {"region_name": settings.FACILITY_S3_REGION}
    if CSProvider.AWS_ROLE_BASED.value != settings.BUCKET_PROVIDER:
        params["aws_access_key_id"] = settings.FACILITY_S3_KEY
        params["aws_secret_access_key"] = settings.FACILITY_S3_SECRET
        params["endpoint_url"] = (
            settings.FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT
            if external
            else settings.FILE_UPLOAD_BUCKET_ENDPOINT
        )
    return params, settings.FILE_UPLOAD_BUCKET


def get_client_config(bucket_type: BucketType, external=False):
    if bucket_type == BucketType.FACILITY:
        return get_facility_bucket_config(external=external)
    if bucket_type == BucketType.PATIENT:
        return get_patient_bucket_config(external=external)
    if bucket_type == BucketType.REPORT:
        return get_report_bucket_config(external=external)
    msg = "Invalid Bucket Type"
    raise ValueError(msg)
