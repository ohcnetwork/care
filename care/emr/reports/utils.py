import hashlib

import requests
from django.core.cache import cache

from care.utils.lock import Lock


def download_image_to_cache(file_name, url):
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_key = f"image_cache:{file_name}:{url_hash}"

    cached_image = cache.get(cache_key)

    if cached_image:
        return cached_image

    with Lock(cache_key):
        cached_image = cache.get(cache_key)
        if cached_image:
            return cached_image

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        cache.set(cache_key, response.content, timeout=24 * 60 * 60)
        return response.content
