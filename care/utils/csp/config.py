import enum

from django.conf import settings


class CSProvider(enum.Enum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"


class BucketType(enum.Enum):
    PATIENT = "PATIENT"
    FACILITY = "FACILITY"


DEFAULT = CSProvider.AWS.value


def get_client_config(bucket_type=BucketType.PATIENT.value):
    config = {
        BucketType.PATIENT.value: {
            "region_name": settings.CLOUD_REGION,
            "aws_access_key_id": settings.FILE_UPLOAD_KEY,
            "aws_secret_access_key": settings.FILE_UPLOAD_SECRET,
            "endpoint_url": settings.FILE_UPLOAD_BUCKET_ENDPOINT,
        },
        BucketType.FACILITY.value: {
            "region_name": settings.CLOUD_REGION,
            "aws_access_key_id": settings.FACILITY_S3_KEY,
            "aws_secret_access_key": settings.FACILITY_S3_SECRET,
            "endpoint_url": settings.FACILITY_S3_BUCKET_ENDPOINT,
        },
    }

    if CSProvider.GCP.value == settings.CLOUD_PROVIDER:
        for key in config:
            config[key]["endpoint_url"] = "https://storage.googleapis.com"

    return config[bucket_type]
