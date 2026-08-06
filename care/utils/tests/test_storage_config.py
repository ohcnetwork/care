"""
Storage configuration tests (ADR-0001 / IS-01).

These cover how the logical aliases are *constructed*. They never contact a
provider: the GCS cases exercise settings construction only and require no
Google credentials.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.storage import (
    GCS_BACKEND,
    S3_BACKEND,
    SUPPORTED_STORAGE_BACKENDS,
    build_object_storage,
    validate_storage_backend,
)

OBJECT_STORAGE_ALIASES = ("patient", "facility", "report")


class StorageBackendValidationTests(SimpleTestCase):
    def test_supported_backends(self):
        self.assertEqual(SUPPORTED_STORAGE_BACKENDS, ("s3", "gcs"))

    def test_valid_backends_accepted(self):
        for backend in SUPPORTED_STORAGE_BACKENDS:
            with self.subTest(backend=backend):
                self.assertEqual(validate_storage_backend(backend), backend)

    def test_invalid_backend_rejected_and_lists_supported_values(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            validate_storage_backend("azure")
        message = str(ctx.exception)
        self.assertIn("azure", message)
        for backend in SUPPORTED_STORAGE_BACKENDS:
            self.assertIn(backend, message)

    def test_build_rejects_invalid_backend(self):
        with self.assertRaises(ImproperlyConfigured):
            build_object_storage("nope", "some-bucket")


class ActiveStorageSettingsTests(SimpleTestCase):
    """The aliases as actually configured for this test run."""

    def test_default_backend_is_s3(self):
        self.assertEqual(settings.CARE_STORAGE_BACKEND, "s3")

    def test_object_aliases_are_configured(self):
        for alias in OBJECT_STORAGE_ALIASES:
            with self.subTest(alias=alias):
                self.assertIn(alias, settings.STORAGES)
                self.assertEqual(settings.STORAGES[alias]["BACKEND"], S3_BACKEND)

    def test_staticfiles_remains_whitenoise(self):
        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )

    def test_aliases_carry_a_bucket(self):
        for alias in OBJECT_STORAGE_ALIASES:
            with self.subTest(alias=alias):
                self.assertTrue(settings.STORAGES[alias]["OPTIONS"]["bucket_name"])

    def test_report_shares_the_patient_bucket_but_stays_a_distinct_alias(self):
        patient = settings.STORAGES["patient"]["OPTIONS"]["bucket_name"]
        report = settings.STORAGES["report"]["OPTIONS"]["bucket_name"]
        self.assertEqual(patient, report)
        self.assertIsNot(settings.STORAGES["patient"], settings.STORAGES["report"])

    def test_alias_names_carry_no_provider_name(self):
        for alias in settings.STORAGES:
            with self.subTest(alias=alias):
                for provider in ("s3", "gcs", "minio", "aws", "google"):
                    self.assertNotIn(provider, alias.lower())


class S3ProfileConstructionTests(SimpleTestCase):
    def test_s3_alias_uses_s3storage(self):
        config = build_object_storage("s3", "patient-bucket")
        self.assertEqual(config["BACKEND"], S3_BACKEND)
        self.assertEqual(config["OPTIONS"]["bucket_name"], "patient-bucket")

    def test_file_overwrite_enabled(self):
        # CARE generates unique internal names and the boto3 put_object this
        # replaces overwrote unconditionally, so Django must not rename.
        config = build_object_storage("s3", "b")
        self.assertTrue(config["OPTIONS"]["file_overwrite"])

    def test_private_by_default(self):
        config = build_object_storage("s3", "b")
        self.assertIsNone(config["OPTIONS"]["default_acl"])

    def test_explicit_acl_is_preserved(self):
        config = build_object_storage("s3", "b", default_acl="public-read")
        self.assertEqual(config["OPTIONS"]["default_acl"], "public-read")

    def test_endpoint_omitted_for_aws(self):
        # Generic AWS S3 has no custom endpoint.
        config = build_object_storage("s3", "b", region_name="ap-south-1")
        self.assertNotIn("endpoint_url", config["OPTIONS"])

    def test_endpoint_included_for_s3_compatible(self):
        config = build_object_storage("s3", "b", endpoint_url="http://minio:9000")
        self.assertEqual(config["OPTIONS"]["endpoint_url"], "http://minio:9000")

    def test_credentials_omitted_when_absent(self):
        # Role-based AWS credentials: boto3 resolves them itself.
        config = build_object_storage("s3", "b", access_key=None, secret_key=None)
        self.assertNotIn("access_key", config["OPTIONS"])
        self.assertNotIn("secret_key", config["OPTIONS"])

    def test_gcs_variables_are_not_required_under_s3(self):
        config = build_object_storage("s3", "b", project_id=None)
        self.assertNotIn("project_id", config["OPTIONS"])


class GCSProfileConstructionTests(SimpleTestCase):
    """Construction only -- no Google credentials and no network access."""

    def test_gcs_alias_uses_google_cloud_storage(self):
        config = build_object_storage("gcs", "patient-bucket")
        self.assertEqual(config["BACKEND"], GCS_BACKEND)
        self.assertEqual(config["OPTIONS"]["bucket_name"], "patient-bucket")

    def test_s3_options_are_not_leaked_into_gcs(self):
        config = build_object_storage(
            "gcs",
            "b",
            region_name="ap-south-1",
            access_key="key",
            secret_key="secret",
            endpoint_url="http://minio:9000",
            default_acl="public-read",
        )
        for option in ("region_name", "access_key", "secret_key", "endpoint_url"):
            self.assertNotIn(option, config["OPTIONS"])

    def test_gcs_never_uses_object_acls(self):
        # Uniform bucket-level access rejects per-object ACLs.
        config = build_object_storage("gcs", "b", default_acl="public-read")
        self.assertIsNone(config["OPTIONS"]["default_acl"])

    def test_project_id_optional(self):
        without = build_object_storage("gcs", "b")
        self.assertNotIn("project_id", without["OPTIONS"])
        with_project = build_object_storage("gcs", "b", project_id="care-project")
        self.assertEqual(with_project["OPTIONS"]["project_id"], "care-project")

    def test_gcs_backend_is_importable_and_constructible_without_credentials(self):
        from django.utils.module_loading import import_string

        backend = import_string(GCS_BACKEND)
        storage = backend(**build_object_storage("gcs", "care-bucket")["OPTIONS"])
        self.assertEqual(storage.bucket_name, "care-bucket")
