import enum
from django.conf import settings


class CSProvider(enum.Enum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"


DEFAULT = CSProvider.AWS.value


def get_client_config():
    config = {
        "region_name": settings.CLOUD_REGION,
        "aws_access_key_id": settings.FILE_UPLOAD_KEY,
        "aws_secret_access_key": settings.FILE_UPLOAD_SECRET,
    }

    if settings.CLOUD_PROVIDER == CSProvider.GCP.value:
        config["endpoint_url"] = "https://storage.googleapis.com"

    return config
