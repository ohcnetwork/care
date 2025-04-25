import logging
import secrets
from typing import Literal

from django.core.files.uploadedfile import UploadedFile

from care.emr.utils.file_manager import get_file_manager
from care.utils.csp.config import BucketType

logger = logging.getLogger(__name__)


def delete_cover_image(image_key: str, folder: Literal["cover_images", "avatars"]):
    file_manager = get_file_manager(BucketType.FACILITY)

    try:
        file_manager._delete_object(image_key)  # noqa: SLF001
    except Exception:
        logger.warning("Failed to delete cover image %s", image_key)


def upload_cover_image(
    image: UploadedFile,
    object_external_id: str,
    folder: Literal["cover_images", "avatars"],
    old_key: str | None = None,
) -> str:
    file_manager = get_file_manager(BucketType.FACILITY)

    if old_key:
        try:
            file_manager._delete_object(old_key)  # noqa: SLF001
        except Exception:
            logger.warning("Failed to delete old cover image %s", old_key)

    image_extension = image.name.rsplit(".", 1)[-1]
    image_key = (
        f"{folder}/{object_external_id}_{secrets.token_hex(8)}.{image_extension}"
    )

    file_manager._put_object(image_key, image.file)  # noqa: SLF001
    return image_key
