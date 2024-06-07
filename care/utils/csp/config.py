import enum
from typing import TypeAlias, TypedDict

from django.conf import settings


class ClientConfig(TypedDict):
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    endpoint_url: str


BucketName: TypeAlias = str


class CSProvider(enum.Enum):
    AWS = "AWS"
    GCP = "GCP"
    DOCKER = "DOCKER"  # localstack in docker
    LOCAL = "LOCAL"  # localstack on host


class BucketType(enum.Enum):
    PATIENT = "PATIENT"
    FACILITY = "FACILITY"
    USER = "USER"


def get_facility_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    return {
        "region_name": settings.FACILITY_S3_REGION,
        "aws_access_key_id": settings.FACILITY_S3_KEY,
        "aws_secret_access_key": settings.FACILITY_S3_SECRET,
        "endpoint_url": settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT
        if external
        else settings.FACILITY_S3_BUCKET_ENDPOINT,
    }, settings.FACILITY_S3_BUCKET


def get_patient_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    return {
        "region_name": settings.FILE_UPLOAD_REGION,
        "aws_access_key_id": settings.FILE_UPLOAD_KEY,
        "aws_secret_access_key": settings.FILE_UPLOAD_SECRET,
        "endpoint_url": settings.FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT
        if external
        else settings.FILE_UPLOAD_BUCKET_ENDPOINT,
    }, settings.FILE_UPLOAD_BUCKET

def get_user_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    return {
        "region_name": settings.USER_S3_REGION,
        "aws_access_key_id": settings.USER_S3_KEY,
        "aws_secret_access_key": settings.USER_S3_SECRET,
        "endpoint_url": settings.USER_S3_BUCKET_EXTERNAL_ENDPOINT
        if external
        else settings.USER_S3_BUCKET_ENDPOINT,
    }, settings.USER_S3_BUCKET

def get_client_config(bucket_type: BucketType, external=False):
    if bucket_type == BucketType.FACILITY:
        return get_facility_bucket_config(external=external)
    elif bucket_type == BucketType.PATIENT:
        return get_patient_bucket_config(external=external)
    elif bucket_type == BucketType.USER:
        return get_user_bucket_config(external=external)
    raise ValueError("Invalid Bucket Type")
