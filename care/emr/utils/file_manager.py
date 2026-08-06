"""
Object persistence for CARE's file models.

ADR-0001 makes Django's Storage API the object-persistence abstraction, so this
module contains no provider SDK import and no provider branch. The provider is
selected entirely in settings; see ``config/storage.py``.

Presigned-URL generation is deliberately *not* here. It is provider-specific and
lives in :mod:`care.emr.utils.legacy_signed_urls` until IS-02 replaces those
flows with Django-served transfers.
"""

import logging

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import storages

logger = logging.getLogger(__name__)


def get_storage_name(file_obj) -> str:
    """
    Return the provider-neutral object name for ``file_obj``.

    The convention is ``<file_type>/<internal_name>``, unchanged from the boto3
    key this replaces. The result is relative: it carries no bucket, no URL and
    no provider endpoint.

    Both components are server-controlled in practice -- ``file_type`` is a
    bounded choice (``FileTypeChoices`` for uploads, the report-type registry
    for reports) and ``internal_name`` is generated from a UUID. The traversal
    guard below is defence in depth, so that a future caller cannot quietly
    write outside the intended prefix.
    """
    file_type = str(file_obj.file_type or "").strip()
    internal_name = str(file_obj.internal_name or "").strip()

    if not file_type or not internal_name:
        msg = "Cannot build a storage name without both file_type and internal_name"
        raise SuspiciousFileOperation(msg)

    name = f"{file_type}/{internal_name}"

    # Reject anything that could escape the prefix. Names are not otherwise
    # normalised: existing objects must stay addressable byte-for-byte.
    if name.startswith(("/", "\\")) or any(
        segment in {"..", ""} for segment in name.replace("\\", "/").split("/")
    ):
        msg = f"Detected path traversal attempt in storage name: {name!r}"
        raise SuspiciousFileOperation(msg)

    return name


class FilesManager:
    """
    Transitional wrapper binding a CARE file model to a logical storage alias.

    Retained rather than removed because ``files_manager`` is a class attribute
    on ``FileUpload`` and ``ReportUpload`` and is referenced from viewsets,
    tasks and report generation; rewriting every caller to use ``storages[...]``
    directly would be a wider change than IS-01 warrants.

    It resolves the alias, generates a provider-neutral object name and
    delegates to Django Storage. It holds no provider SDK import, no provider
    branch, and returns no provider response object. It is *not* the permanent
    storage abstraction -- ``django.core.files.storage.storages`` is.
    """

    def __init__(self, storage_alias: str):
        self.storage_alias = storage_alias

    @property
    def storage(self):
        """The Django ``Storage`` backing this alias."""
        return storages[self.storage_alias]

    def put_object(self, file_obj, file, content_type: str | None = None) -> str:
        """
        Write ``file`` and return the stored object name.

        ``file`` may be any Django file or file-like object; it is passed
        through without being read into memory here.

        ``content_type`` is an optional hint. ``S3Storage`` prefers it over the
        name; ``GoogleCloudStorage`` derives the type from the name's extension
        instead, so the extension carried by ``internal_name`` remains the
        portable signal.
        """
        name = get_storage_name(file_obj)
        if content_type is not None:
            file.content_type = content_type
        return self.storage.save(name, file)

    def get_object(self, file_obj, mode: str = "rb"):
        """
        Open the object and return a file-like object.

        Raises ``FileNotFoundError`` when the object does not exist. The caller
        is responsible for closing it; prefer using it as a context manager.
        """
        return self.storage.open(get_storage_name(file_obj), mode)

    def file_contents(self, file_obj) -> bytes:
        """
        Read the whole object into memory.

        Only for callers that genuinely need the complete bytes. Prefer
        :meth:`get_object` as a context manager.
        """
        with self.get_object(file_obj) as file:
            return file.read()

    def delete_object(self, file_obj) -> None:
        """
        Delete the object.

        Deleting a missing object is not an error. That matches Django Storage
        on both backends and the behaviour it replaces: S3 ``delete_object`` is
        idempotent, so the previous ``NoSuchKey`` branch never actually fired.
        """
        self.storage.delete(get_storage_name(file_obj))

    def exists(self, file_obj) -> bool:
        return self.storage.exists(get_storage_name(file_obj))

    def size(self, file_obj) -> int:
        return self.storage.size(get_storage_name(file_obj))
