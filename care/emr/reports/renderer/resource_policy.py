"""Shared policy for remote assets in HTML and PDF reports."""

from urllib.parse import urlsplit

from django.conf import settings

IMAGE_MIME_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/webp", "image/avif", "image/bmp"}
)
FONT_MIME_TYPES = frozenset(
    {
        "font/ttf",
        "font/otf",
        "font/woff",
        "font/woff2",
        "application/font-woff",
        "application/font-sfnt",
        "application/x-font-woff",
        "application/x-font-ttf",
        "application/x-font-opentype",
        "application/vnd.ms-opentype",
    }
)


def _https_origin(url):
    if "\\" in url or any(ord(char) <= 32 or ord(char) == 127 for char in url):  # noqa: PLR2004
        return None
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        port = parsed.port if parsed.port is not None else 443
    except ValueError:
        return None
    return parsed.hostname, port


def is_allowed_remote_resource(url):
    origin = _https_origin(url)
    if origin is None:
        return False
    for allowed in settings.REPORT_ALLOWED_RESOURCE_ORIGINS:
        if _https_origin(allowed) != origin:
            continue
        parsed = urlsplit(allowed)
        if parsed.path in {"", "/"} and not parsed.query and not parsed.fragment:
            return True
    return False
