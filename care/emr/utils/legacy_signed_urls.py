"""
Legacy presigned-URL generation. Transitional; removed by IS-02.

ADR-0001 covers object *persistence* only, and Django's Storage API has no
portable presigned-URL operation. These two functions are therefore the one
place where a provider SDK is still used for file handling, kept isolated from
ordinary CRUD (which lives in :mod:`care.emr.utils.file_manager` and goes
through Django Storage).

They are S3-only. Selecting ``CARE_STORAGE_BACKEND=gcs`` configures persistence
against Google Cloud Storage but does **not** make these work; that is accepted
for now because IS-02 removes both flows.

No new feature may depend on this module.

Exact callers as of IS-01:

``signed_url`` (browser-to-bucket upload)
    - ``care/emr/resources/file_upload/spec.py``
    - ``care/emr/resources/report/report_upload/spec.py``

``read_signed_url`` (browser-from-bucket download)
    - ``care/emr/resources/file_upload/spec.py``
    - ``care/emr/resources/report/report_upload/spec.py``
    - ``care/emr/reports/context_builder/data_points/fileupload.py``
"""

import boto3

from care.emr.utils.file_manager import get_storage_name
from care.utils.csp.config import BucketType, get_client_config

#: MIME types a browser may render inline; everything else downloads.
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

#: Logical storage alias -> the legacy bucket type used to resolve credentials.
_ALIAS_BUCKET_TYPES = {
    "patient": BucketType.PATIENT,
    "facility": BucketType.FACILITY,
    "report": BucketType.REPORT,
}


def _client_for(file_obj):
    """Build an S3 client and bucket name for ``file_obj``'s storage alias."""
    bucket_type = _ALIAS_BUCKET_TYPES[file_obj.files_manager.storage_alias]
    config, bucket_name = get_client_config(bucket_type, external=True)
    return boto3.client("s3", **config), bucket_name


def signed_url(file_obj, duration=60 * 60, mime_type=None):
    """Presigned PUT URL, for direct browser-to-bucket upload."""
    s3, bucket_name = _client_for(file_obj)
    params = {"Bucket": bucket_name, "Key": get_storage_name(file_obj)}

    _mime_type = file_obj.meta.get("mime_type") or mime_type
    if _mime_type:
        params["ContentType"] = _mime_type
    return s3.generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=duration,  # seconds
    )


def read_signed_url(file_obj, duration=60 * 60):
    """Presigned GET URL, for direct browser-from-bucket download."""
    s3, bucket_name = _client_for(file_obj)

    mime_type = file_obj.meta.get("mime_type")
    content_disposition = (
        "inline" if mime_type in SAFE_INLINE_FORMATS else "attachment"
    )

    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket_name,
            "Key": get_storage_name(file_obj),
            "ResponseContentDisposition": f"{content_disposition}; filename={file_obj.name}{file_obj.get_extension()}",
        },
        ExpiresIn=duration,  # seconds
    )
