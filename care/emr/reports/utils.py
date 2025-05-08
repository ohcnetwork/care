import hashlib

import magic
import requests
from django.conf import settings
from django.core.cache import cache

from care.utils.lock import Lock


def download_image_to_cache(file_name: str, url: str) -> bytes:
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_key = f"image_cache:{file_name}:{url_hash}"

    cached_image = cache.get(cache_key)
    if cached_image:
        return cached_image

    with Lock(cache_key):
        cached_image = cache.get(cache_key)
        if cached_image:
            return cached_image

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            error = f"Failed to download image from {url}. Please Recheck the URL."
            raise ValueError(error) from e

        image_bytes = response.content

        if len(image_bytes) > settings.MAX_IMAGE_SIZE_FOR_REPORTS * 1024 * 1024:
            error = f"Image from {url} exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_FOR_REPORTS}MB"
            raise ValueError(error)

        mime_type = magic.from_buffer(image_bytes, mime=True)
        allowed_mime_types = {
            "image/svg+xml",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
        }

        if mime_type not in allowed_mime_types:
            error = f"Invalid image format '{mime_type}' from URL: {url}"
            raise ValueError(error)

        cache.set(cache_key, image_bytes, timeout=24 * 60 * 60)
        return image_bytes
