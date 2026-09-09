"""
Storage behaviour tests (ADR-0001 / IS-01).

Three groups:

- object-name generation, which must stay byte-for-byte compatible;
- delegation through Django Storage, proven with an in-memory backend at the
  Django Storage boundary rather than by mocking a provider SDK;
- real MinIO integration through the configured aliases.
"""

import uuid
from types import SimpleNamespace

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import SimpleTestCase, override_settings

from care.emr.models.file_upload import FileUpload
from care.emr.models.report.report_upload import ReportUpload
from care.emr.utils.file_manager import FilesManager, get_storage_name

IN_MEMORY = "django.core.files.storage.InMemoryStorage"


def file_stub(file_type, internal_name):
    return SimpleNamespace(file_type=file_type, internal_name=internal_name)


def unique_name():
    return f"is01-test-{uuid.uuid4()}"


class StorageNameTests(SimpleTestCase):
    def test_convention_is_file_type_slash_internal_name(self):
        self.assertEqual(
            get_storage_name(file_stub("patient", "abc123")), "patient/abc123"
        )

    def test_each_logical_file_type(self):
        for file_type in ("patient", "encounter", "consent", "diagnostic_report"):
            with self.subTest(file_type=file_type):
                self.assertEqual(
                    get_storage_name(file_stub(file_type, "obj")), f"{file_type}/obj"
                )

    def test_extension_preserved(self):
        self.assertEqual(
            get_storage_name(file_stub("patient", "abc.tar.gz")), "patient/abc.tar.gz"
        )

    def test_unicode_preserved(self):
        name = get_storage_name(file_stub("patient", "rapport-café-日本語.pdf"))
        self.assertEqual(name, "patient/rapport-café-日本語.pdf")

    def test_unusual_but_valid_names_preserved(self):
        for internal_name in ("a b c.png", "file(1).pdf", "'quoted'.txt", "a+b=c.bin"):
            with self.subTest(internal_name=internal_name):
                self.assertEqual(
                    get_storage_name(file_stub("patient", internal_name)),
                    f"patient/{internal_name}",
                )

    def test_name_is_relative(self):
        name = get_storage_name(file_stub("patient", "abc"))
        self.assertFalse(name.startswith("/"))
        self.assertNotIn("://", name)
        self.assertNotIn("patient-bucket", name)

    def test_path_traversal_rejected(self):
        traversals = [
            ("../etc", "passwd"),
            ("patient", "../../etc/passwd"),
            ("patient", ".."),
            ("..", ".."),
            ("patient", "..\\..\\windows"),
        ]
        for file_type, internal_name in traversals:
            with (
                self.subTest(file_type=file_type, internal_name=internal_name),
                self.assertRaises(SuspiciousFileOperation),
            ):
                get_storage_name(file_stub(file_type, internal_name))

    def test_absolute_paths_rejected(self):
        with self.assertRaises(SuspiciousFileOperation):
            get_storage_name(file_stub("/patient", "abc"))

    def test_empty_components_rejected(self):
        for file_type, internal_name in (("", "abc"), ("patient", ""), (None, None)):
            with (
                self.subTest(file_type=file_type, internal_name=internal_name),
                self.assertRaises(SuspiciousFileOperation),
            ):
                get_storage_name(file_stub(file_type, internal_name))


class AliasMappingTests(SimpleTestCase):
    def test_models_are_bound_to_logical_aliases(self):
        self.assertEqual(FileUpload.files_manager.storage_alias, "patient")
        self.assertEqual(ReportUpload.files_manager.storage_alias, "report")

    def test_cover_images_use_the_facility_alias(self):
        from care.utils.file_uploads import cover_image

        self.assertEqual(cover_image.STORAGE_ALIAS, "facility")

    def test_report_uses_report_type_as_file_type(self):
        report = ReportUpload(report_type="discharge", internal_name="abc")
        self.assertEqual(get_storage_name(report), "discharge/abc")


@override_settings(
    STORAGES={
        "staticfiles": {"BACKEND": IN_MEMORY},
        "patient": {"BACKEND": IN_MEMORY},
        "facility": {"BACKEND": IN_MEMORY},
        "report": {"BACKEND": IN_MEMORY},
    }
)
class FilesManagerDelegationTests(SimpleTestCase):
    """
    Proves FilesManager delegates to whatever Django Storage backs the alias.

    No provider SDK is mocked; substituting the backend is the whole point.
    """

    def setUp(self):
        self.manager = FilesManager("patient")
        self.file_obj = file_stub("patient", unique_name())

    def test_uses_the_backend_configured_for_its_alias(self):
        self.assertEqual(
            type(self.manager.storage), type(storages["patient"])
        )

    def test_save_uses_the_storage_name_convention(self):
        name = self.manager.put_object(self.file_obj, ContentFile(b"data"))
        self.assertEqual(name, get_storage_name(self.file_obj))
        self.assertTrue(self.manager.storage.exists(name))

    def test_content_round_trip(self):
        self.manager.put_object(self.file_obj, ContentFile(b"clinical bytes"))
        with self.manager.get_object(self.file_obj) as handle:
            self.assertEqual(handle.read(), b"clinical bytes")

    def test_file_contents_returns_bytes(self):
        self.manager.put_object(self.file_obj, ContentFile(b"payload"))
        self.assertEqual(self.manager.file_contents(self.file_obj), b"payload")

    def test_exists_and_size(self):
        self.assertFalse(self.manager.exists(self.file_obj))
        self.manager.put_object(self.file_obj, ContentFile(b"12345"))
        self.assertTrue(self.manager.exists(self.file_obj))
        self.assertEqual(self.manager.size(self.file_obj), 5)

    def test_delete(self):
        self.manager.put_object(self.file_obj, ContentFile(b"x"))
        self.manager.delete_object(self.file_obj)
        self.assertFalse(self.manager.exists(self.file_obj))

    def test_deleting_a_missing_object_is_not_an_error(self):
        self.manager.delete_object(self.file_obj)

    def test_put_object_returns_the_name_the_backend_chose(self):
        # Overwrite-on-collision is a backend option (file_overwrite), not a
        # Django Storage guarantee: InMemoryStorage renames instead. What
        # FilesManager guarantees is that it reports back what the backend did.
        # The overwrite behaviour CARE actually relies on is asserted against
        # the configured backends in MinioIntegrationTests, and the option
        # itself in care.utils.tests.test_storage_config.
        first = self.manager.put_object(self.file_obj, ContentFile(b"first"))
        second = self.manager.put_object(self.file_obj, ContentFile(b"second"))
        self.assertEqual(first, get_storage_name(self.file_obj))
        self.assertTrue(self.manager.storage.exists(second))
        with self.manager.storage.open(second, "rb") as handle:
            self.assertEqual(handle.read(), b"second")

    def test_aliases_are_independent(self):
        report_manager = FilesManager("report")
        self.manager.put_object(self.file_obj, ContentFile(b"patient copy"))
        self.assertFalse(report_manager.exists(self.file_obj))


class MinioIntegrationTests(SimpleTestCase):
    """
    Mandatory local profile (IS-01 section 27.5): MinIO through S3Storage,
    exercised against the running compose service via the real aliases.

    Names are UUID-based so parallel workers sharing one MinIO cannot collide.
    """

    aliases = ("patient", "facility", "report")

    def test_aliases_are_s3_storage(self):
        for alias in self.aliases:
            with self.subTest(alias=alias):
                self.assertEqual(type(storages[alias]).__name__, "S3Storage")

    def test_round_trip_on_every_alias(self):
        for alias in self.aliases:
            with self.subTest(alias=alias):
                storage = storages[alias]
                name = f"is01-integration/{uuid.uuid4()}.txt"
                payload = f"care {alias}".encode()
                try:
                    saved = storage.save(name, ContentFile(payload))
                    self.assertEqual(saved, name)
                    self.assertTrue(storage.exists(saved))
                    self.assertEqual(storage.size(saved), len(payload))
                    with storage.open(saved, "rb") as handle:
                        self.assertEqual(handle.read(), payload)
                finally:
                    storage.delete(name)
                self.assertFalse(storage.exists(name))

    def test_missing_object_raises_file_not_found(self):
        storage = storages["patient"]
        with self.assertRaises(FileNotFoundError):
            storage.open(f"is01-integration/missing-{uuid.uuid4()}", "rb")

    def test_deleting_a_missing_object_is_not_an_error(self):
        storages["patient"].delete(f"is01-integration/missing-{uuid.uuid4()}")

    def test_overwrite_keeps_the_name(self):
        storage = storages["patient"]
        name = f"is01-integration/{uuid.uuid4()}.txt"
        try:
            storage.save(name, ContentFile(b"first"))
            self.assertEqual(storage.save(name, ContentFile(b"second")), name)
            with storage.open(name, "rb") as handle:
                self.assertEqual(handle.read(), b"second")
        finally:
            storage.delete(name)

    def test_manager_round_trip_against_minio(self):
        manager = FilesManager("patient")
        file_obj = file_stub("patient", f"{uuid.uuid4()}.txt")
        try:
            manager.put_object(file_obj, ContentFile(b"through the manager"))
            self.assertTrue(manager.exists(file_obj))
            self.assertEqual(manager.file_contents(file_obj), b"through the manager")
        finally:
            manager.delete_object(file_obj)
        self.assertFalse(manager.exists(file_obj))
