"""
Django-mediated object download.

ADR-0001: a client never receives a storage-provider URL. Every read of a stored
object is served by CARE, streaming through Django Storage, so the bucket stays
private and the provider stays interchangeable.

This module contains no provider SDK import and no provider branch.
"""

import mimetypes

from django.http import FileResponse
from django.urls import reverse
from rest_framework.exceptions import NotFound

from care.emr.utils.file_manager import get_storage_name

#: MIME types a browser may render inline; everything else downloads.
#: Preserved from the presigned ``ResponseContentDisposition`` behaviour this
#: replaces, so browser handling of patient documents is unchanged.
SAFE_INLINE_FORMATS = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "image/bmp",
    "image/x-icon",
    "application/pdf",
}


def storage_file_response(storage, name, *, filename, mime_type=None):
    """
    Stream ``name`` from ``storage`` as an HTTP response.

    ``FileResponse`` streams in chunks and closes the handle when the response
    is finished, so the object is never fully buffered in memory.
    """
    if not mime_type:
        mime_type = mimetypes.guess_type(filename or name)[0]
    mime_type = mime_type or "application/octet-stream"

    try:
        handle = storage.open(name, "rb")
    except FileNotFoundError as e:
        msg = "File not found in storage"
        raise NotFound(msg) from e

    return FileResponse(
        handle,
        as_attachment=mime_type not in SAFE_INLINE_FORMATS,
        filename=filename,
        content_type=mime_type,
    )


def file_object_response(file_obj):
    """Stream a ``FileUpload`` or ``ReportUpload`` through Django Storage."""
    return storage_file_response(
        file_obj.files_manager.storage,
        get_storage_name(file_obj),
        filename=f"{file_obj.name}{file_obj.get_extension()}",
        mime_type=file_obj.meta.get("mime_type"),
    )


def file_download_url(file_obj) -> str:
    """CARE download route for a ``FileUpload``."""
    return reverse("files-download", kwargs={"external_id": file_obj.external_id})


def report_download_url(report_obj) -> str:
    """CARE download route for a ``ReportUpload``."""
    return reverse(
        "template-reports-download", kwargs={"external_id": report_obj.external_id}
    )
