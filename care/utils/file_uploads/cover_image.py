import logging
import secrets
from typing import Literal

from django.core.files.storage import storages
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)

#: Cover images and avatars keep their own key convention,
#: ``<folder>/<external_id>_<token>.<ext>``, which is unrelated to the
#: ``<file_type>/<internal_name>`` convention used by FileUpload/ReportUpload.
#: They are therefore addressed through the alias directly rather than through
#: FilesManager.
STORAGE_ALIAS = "facility"


def delete_cover_image(image_key: str, folder: Literal["cover_images", "avatars"]):
    try:
        storages[STORAGE_ALIAS].delete(image_key)
    except Exception:
        logger.warning("Failed to delete cover image %s", image_key)


def upload_cover_image(
    image: UploadedFile,
    object_external_id: str,
    folder: Literal["cover_images", "avatars"],
    old_key: str | None = None,
) -> str:
    storage = storages[STORAGE_ALIAS]

    if old_key:
        try:
            storage.delete(old_key)
        except Exception:
            logger.warning("Failed to delete old cover image %s", old_key)

    image_extension = image.name.rsplit(".", 1)[-1]
    image_key = (
        f"{folder}/{object_external_id}_{secrets.token_hex(8)}.{image_extension}"
    )

    # No ACL is set: the object is private and served by CARE through the
    # public asset routes (ADR-0001). The uploaded file is passed through
    # rather than read into memory.
    return storage.save(image_key, image)
