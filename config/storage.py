"""
Construction of CARE's logical object-storage aliases.

ADR-0001 makes Django's Storage API the object-persistence abstraction and
delegates provider implementations to ``django-storages``. Provider selection is
a configuration concern only: application code addresses the logical aliases
``patient``, ``facility`` and ``report`` and never learns which provider serves
them.

This module is settings-level configuration code. It is deliberately *not* an
application storage framework -- application code must never import it and must
use ``django.core.files.storage.storages`` instead.
"""

from django.core.exceptions import ImproperlyConfigured

S3_BACKEND = "storages.backends.s3.S3Storage"
GCS_BACKEND = "storages.backends.gcloud.GoogleCloudStorage"

#: Values accepted by the ``CARE_STORAGE_BACKEND`` setting.
SUPPORTED_STORAGE_BACKENDS = ("s3", "gcs")

#: ``BUCKET_PROVIDER`` value meaning "resolve AWS credentials from the instance
#: role" -- key and secret are then omitted entirely.
AWS_ROLE_BASED_BUCKET_PROVIDER = "AWS_ROLE_BASED"


def validate_storage_backend(backend: str) -> str:
    """Return ``backend`` if supported, otherwise raise ``ImproperlyConfigured``."""
    if backend not in SUPPORTED_STORAGE_BACKENDS:
        supported = ", ".join(SUPPORTED_STORAGE_BACKENDS)
        msg = (
            f"Invalid CARE_STORAGE_BACKEND: {backend!r}. "
            f"Supported values are: {supported}."
        )
        raise ImproperlyConfigured(msg)
    return backend


def build_object_storage(
    backend: str,
    bucket_name: str,
    *,
    region_name: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    endpoint_url: str | None = None,
    project_id: str | None = None,
) -> dict:
    """
    Build a single ``STORAGES`` entry for one logical alias.

    Only options that carry a value are emitted, so that:

    - AWS S3 works without ``endpoint_url``;
    - role-based AWS credentials work when no key/secret is supplied;
    - Google Cloud Storage uses Application Default Credentials.

    ``file_overwrite`` is set explicitly rather than left to the backend
    default. CARE generates a unique ``internal_name`` per object and the
    behaviour it replaces (``boto3.put_object``) overwrites unconditionally, so
    Django must not rename on collision.

    No alias is ever public. Every object is served by CARE through Django
    Storage (ADR-0001), so buckets can and should be private.
    """
    validate_storage_backend(backend)

    if backend == "gcs":
        options: dict = {
            "bucket_name": bucket_name,
            "file_overwrite": True,
            # Uniform bucket-level access: never per-object ACLs (ADR-0001).
            "default_acl": None,
        }
        if project_id:
            options["project_id"] = project_id
        return {"BACKEND": GCS_BACKEND, "OPTIONS": options}

    options = {
        "bucket_name": bucket_name,
        "file_overwrite": True,
        # Private: CARE serves every object, so no public ACL is ever needed.
        "default_acl": None,
    }
    if region_name:
        options["region_name"] = region_name
    if access_key:
        options["access_key"] = access_key
    if secret_key:
        options["secret_key"] = secret_key
    if endpoint_url:
        options["endpoint_url"] = endpoint_url
    return {"BACKEND": S3_BACKEND, "OPTIONS": options}
