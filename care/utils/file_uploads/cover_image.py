import logging
import secrets
from typing import Literal

import boto3
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from care.utils.csp.config import BucketType, get_client_config

logger = logging.getLogger(__name__)


def delete_cover_image(image_key: str, folder: Literal["cover_images", "avatars"]):
    config, bucket_name = get_client_config(BucketType.FACILITY)
    s3 = boto3.client("s3", **config)

    try:
        s3.delete_object(Bucket=bucket_name, Key=image_key)
    except Exception:
        logger.warning("Failed to delete cover image %s", image_key)


def upload_cover_image(
    image: UploadedFile,
    object_external_id: str,
    folder: Literal["cover_images", "avatars"],
    old_key: str | None = None,
) -> str:
    config, bucket_name = get_client_config(BucketType.FACILITY)
    s3 = boto3.client("s3", **config)

    if old_key:
        try:
            s3.delete_object(Bucket=bucket_name, Key=old_key)
        except Exception:
            logger.warning("Failed to delete old cover image %s", old_key)

    image_extension = image.name.rsplit(".", 1)[-1]
    image_key = (
        f"{folder}/{object_external_id}_{secrets.token_hex(8)}.{image_extension}"
    )

    boto_params = {
        "Bucket": bucket_name,
        "Key": image_key,
        "Body": image.file,
    }
    if settings.BUCKET_HAS_FINE_ACL:
        boto_params["ACL"] = "public-read"
    s3.put_object(**boto_params)

    return image_key
