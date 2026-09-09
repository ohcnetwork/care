"""
Multipart upload transport tests (ADR-0002 / ES-02).

Covers the HTTP transport contract: what the endpoint accepts, what it rejects,
how it behaves under failure, and that it stays provider-neutral. Persistence
behaviour itself is covered by the ES-01 storage tests.
"""

import io
from unittest.mock import patch

from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    SimpleUploadedFile,
    TemporaryUploadedFile,
)
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from care.emr.models.file_upload import FileUpload
from care.emr.utils.file_manager import FilesManager, get_storage_name
from care.utils.tests.base import CareAPITestBase, response_content


def jpeg_bytes(size=(800, 800)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size).save(buffer, format="JPEG")
    return buffer.getvalue()


class MultipartUploadTestBase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.payload_bytes = jpeg_bytes()
        self.url = reverse("files-upload-file")
        self.client.force_authenticate(user=self.user)

    def upload(
        self,
        *,
        content=None,
        filename="scan.jpg",
        content_type="image/jpeg",
        **overrides,
    ):
        body = {
            "file": SimpleUploadedFile(
                filename,
                self.payload_bytes if content is None else content,
                content_type=content_type,
            ),
            "name": "scan",
            "file_type": "patient",
            "file_category": "unspecified",
            "associating_id": str(self.patient.external_id),
        }
        body.update(overrides)
        body = {k: v for k, v in body.items() if v is not None}
        return self.client.post(self.url, body, format="multipart")


class SuccessfulUploadTests(MultipartUploadTestBase):
    def test_upload_succeeds(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.data)

    def test_record_is_correct(self):
        response = self.upload()
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertEqual(file_obj.name, "scan")
        self.assertEqual(file_obj.file_type, "patient")
        self.assertEqual(file_obj.file_category, "unspecified")
        self.assertEqual(file_obj.associating_id, str(self.patient.external_id))
        self.assertEqual(file_obj.meta["mime_type"], "image/jpeg")
        self.assertTrue(file_obj.upload_completed)

    def test_original_name_defaults_to_the_uploaded_filename(self):
        response = self.upload(filename="referral.jpg")
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        # internal_name is regenerated but keeps the extension.
        self.assertTrue(file_obj.internal_name.endswith(".jpg"))

    def test_explicit_original_name_is_honoured(self):
        response = self.upload(filename="scan.jpg", original_name="override.jpeg")
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertTrue(file_obj.internal_name.endswith(".jpeg"))

    def test_uses_the_patient_alias_and_es01_object_name(self):
        response = self.upload()
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertEqual(file_obj.files_manager.storage_alias, "patient")
        # The ES-01 naming helper remains authoritative; transport adds none.
        self.assertEqual(
            get_storage_name(file_obj), f"patient/{file_obj.internal_name}"
        )
        self.assertTrue(file_obj.files_manager.exists(file_obj))

    def test_stored_bytes_match_and_download_works(self):
        response = self.upload()
        download = self.client.get(response.data["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertEqual(response_content(download), self.payload_bytes)

    def test_response_is_provider_neutral(self):
        response = self.upload()
        body = str(response.data)
        for forbidden in (
            "signed_url",
            "read_signed_url",
            "minio",
            "amazonaws",
            "storage.googleapis",
            "X-Amz-Signature",
            ":9100",
            "patient-bucket",
        ):
            self.assertNotIn(forbidden, body, forbidden)

    def test_response_exposes_no_bucket_or_endpoint_key(self):
        response = self.upload()
        for key in ("bucket", "endpoint", "signed_url", "read_signed_url"):
            self.assertNotIn(key, response.data)


class RejectionTests(MultipartUploadTestBase):
    def test_missing_file_is_rejected(self):
        response = self.upload(file=None)
        self.assertEqual(response.status_code, 400, response.data)

    def test_missing_metadata_is_rejected(self):
        response = self.upload(associating_id=None)
        self.assertEqual(response.status_code, 400, response.data)

    def test_base64_payload_is_no_longer_accepted(self):
        # The old contract must not work, even by accident.
        response = self.client.post(
            self.url,
            {
                "name": "scan",
                "original_name": "scan.jpg",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "file_data": "/9j/4AAQSkZJRgABAQAAAQABAAD//gA7Q1JFQVRPUg==",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.data)

    @override_settings(MAX_FILE_UPLOAD_SIZE=1)
    def test_oversized_file_is_rejected(self):
        response = self.upload(content=b"x" * (2 * 1024 * 1024))
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("size", str(response.data).lower())

    def test_oversized_file_is_not_persisted(self):
        with override_settings(MAX_FILE_UPLOAD_SIZE=1):
            self.upload(content=b"x" * (2 * 1024 * 1024))
        self.assertFalse(FileUpload.objects.exists())


class ValidationTests(MultipartUploadTestBase):
    """MIME is sniffed from content; the declared part header is not trusted."""

    def test_allowed_mime_accepted(self):
        self.assertEqual(self.upload().status_code, 200)

    def test_disallowed_content_rejected_despite_allowed_declared_type(self):
        # Declares image/jpeg but the bytes are a shell script.
        response = self.upload(
            content=b"#!/bin/sh\necho pwned\n",
            filename="payload.jpg",
            content_type="image/jpeg",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("not allowed", str(response.data))

    def test_declared_mime_is_ignored_in_favour_of_content(self):
        # Declares an unsafe type but the bytes are a real JPEG.
        response = self.upload(content=jpeg_bytes(), content_type="application/x-sh")
        self.assertEqual(response.status_code, 200, response.data)
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertEqual(file_obj.meta["mime_type"], "image/jpeg")

    def test_missing_declared_mime_is_fine(self):
        response = self.upload(content_type="")
        self.assertEqual(response.status_code, 200, response.data)

    def test_blocked_extension_is_rejected(self):
        response = self.upload(filename="payload.exe")
        self.assertEqual(response.status_code, 400, response.data)

    def test_uppercase_extension_is_accepted(self):
        response = self.upload(filename="SCAN.JPG")
        self.assertEqual(response.status_code, 200, response.data)

    def test_double_extension_uses_the_outermost(self):
        response = self.upload(filename="scan.jpg.exe")
        self.assertEqual(response.status_code, 400, response.data)

    def test_unknown_file_type_is_rejected(self):
        response = self.upload(file_type="not_a_type")
        self.assertEqual(response.status_code, 400, response.data)

    def test_unknown_file_category_is_rejected(self):
        response = self.upload(file_category="not_a_category")
        self.assertEqual(response.status_code, 400, response.data)


class AuthorizationTests(MultipartUploadTestBase):
    def test_unauthenticated_upload_is_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.upload()
        self.assertIn(response.status_code, (401, 403), response.status_code)

    def test_unauthorized_user_cannot_upload_for_a_patient(self):
        self.client.force_authenticate(user=self.create_user())
        response = self.upload()
        self.assertEqual(response.status_code, 403, response.data)

    def test_unauthorized_upload_persists_nothing(self):
        self.client.force_authenticate(user=self.create_user())
        self.upload()
        self.assertFalse(FileUpload.objects.exists())


class UploadHandlerTests(MultipartUploadTestBase):
    """Django's upload handlers decide memory vs temporary file."""

    def captured_upload(self, content):
        seen = {}
        original = FileUpload.files_manager.__class__.put_object

        def spy(self, file_obj, file, content_type=None):
            seen["type"] = type(file)
            return original(self, file_obj, file, content_type=content_type)

        with patch.object(FileUpload.files_manager.__class__, "put_object", spy):
            response = self.upload(content=content)
        return response, seen.get("type")

    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1024 * 1024)
    def test_small_upload_stays_in_memory(self):
        response, handler_type = self.captured_upload(jpeg_bytes((80, 80)))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIs(handler_type, InMemoryUploadedFile)

    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1024)
    def test_large_upload_is_backed_by_a_temporary_file(self):
        response, handler_type = self.captured_upload(jpeg_bytes((800, 800)))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIs(handler_type, TemporaryUploadedFile)

    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1024)
    def test_temporary_file_upload_round_trips(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.data)
        download = self.client.get(response.data["download_url"])
        self.assertEqual(response_content(download), self.payload_bytes)


class FailureConsistencyTests(MultipartUploadTestBase):
    """Storage and PostgreSQL do not share a transaction; check the seam."""

    def test_storage_failure_reports_failure(self):
        with patch.object(
            FileUpload.files_manager.__class__,
            "put_object",
            side_effect=OSError("storage down"),
        ):
            response = self.upload()
        self.assertEqual(response.status_code, 400, response.data)

    def test_storage_failure_leaves_no_database_row(self):
        with patch.object(
            FileUpload.files_manager.__class__,
            "put_object",
            side_effect=OSError("storage down"),
        ):
            self.upload()
        self.assertFalse(FileUpload.objects.exists())

    def test_database_failure_rolls_the_row_back(self):
        # The completion save fails after the object is written. The row is
        # rolled back; the orphan object is the pre-existing B8 gap.
        #
        # The failure is *not* translated into "failed to upload to storage":
        # storage succeeded. It propagates as a server error, because a database
        # outage is not something the client can fix by changing its request.
        original_save = FileUpload.save
        completion_save = 2  # first save creates the row, second completes it
        calls = {"n": 0}

        def failing_save(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] >= completion_save:
                msg = "db down"
                raise OSError(msg)
            return original_save(self, *args, **kwargs)

        with patch.object(FileUpload, "save", failing_save), self.assertRaises(OSError):
            self.upload()
        self.assertFalse(FileUpload.objects.exists())

    def test_multipart_upload_leaves_no_incomplete_row(self):
        # cleanup_incomplete_file_uploads keys off upload_completed=False. The
        # multipart path writes the object and sets the flag in one request, so
        # a successful upload leaves nothing for the sweeper to collect.
        response = self.upload()
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertTrue(file_obj.upload_completed)
        self.assertTrue(file_obj.files_manager.exists(file_obj))

    def test_storage_failure_is_reported_as_a_storage_failure(self):
        # The other half of the split: a storage error keeps its own message and
        # is still a 400, as before.
        with patch.object(
            FilesManager, "put_object", side_effect=OSError("bucket down")
        ):
            response = self.upload()
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("storage", str(response.data).lower())
        self.assertFalse(FileUpload.objects.exists())


IN_MEMORY = "django.core.files.storage.InMemoryStorage"


class ProviderNeutralTransportTests(MultipartUploadTestBase):
    """
    The transport must not assume a provider (ES-02 section 33).

    Substituting a completely unrelated backend at the Django Storage boundary
    is the strongest available proof: if any S3 assumption survived in the
    upload path, an in-memory backend would break it.
    """

    @override_settings(
        STORAGES={
            "staticfiles": {"BACKEND": IN_MEMORY},
            "patient": {"BACKEND": IN_MEMORY},
            "facility": {"BACKEND": IN_MEMORY},
            "report": {"BACKEND": IN_MEMORY},
        }
    )
    def test_upload_works_against_a_substituted_backend(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.data)
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertEqual(file_obj.files_manager.storage_alias, "patient")
        self.assertTrue(file_obj.files_manager.exists(file_obj))
        self.assertEqual(
            file_obj.files_manager.file_contents(file_obj), self.payload_bytes
        )

    @override_settings(
        STORAGES={
            "staticfiles": {"BACKEND": IN_MEMORY},
            "patient": {"BACKEND": IN_MEMORY},
            "facility": {"BACKEND": IN_MEMORY},
            "report": {"BACKEND": IN_MEMORY},
        }
    )
    def test_download_works_against_a_substituted_backend(self):
        response = self.upload()
        download = self.client.get(response.data["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertEqual(response_content(download), self.payload_bytes)

    def test_transport_modules_do_not_branch_on_the_configured_provider(self):
        # Inspect the AST rather than the text: these modules legitimately
        # mention boto3 and the backend classes in prose, explaining what they
        # replaced. What matters is that no *code* references them.
        import ast
        import inspect

        from care.emr.api.viewsets import file_upload as upload_module
        from care.emr.utils import file_download, file_manager

        forbidden_roots = {"boto3", "botocore", "google", "storages"}

        for module in (upload_module, file_download, file_manager):
            tree = ast.parse(inspect.getsource(module))
            imported = set()
            attributes = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
                elif isinstance(node, ast.Attribute):
                    attributes.add(node.attr)

            with self.subTest(module=module.__name__):
                self.assertEqual(
                    imported & forbidden_roots,
                    set(),
                    f"{module.__name__} imports a provider SDK",
                )
                self.assertNotIn(
                    "CARE_STORAGE_BACKEND",
                    attributes,
                    f"{module.__name__} branches on the configured provider",
                )


class UploadSchemaTests(CareAPITestBase):
    """The generated OpenAPI schema must describe multipart, not JSON."""

    def schema(self):
        from drf_spectacular.generators import SchemaGenerator

        return SchemaGenerator().get_schema(request=None, public=True)

    def upload_operation(self):
        return self.schema()["paths"]["/api/v1/files/upload-file/"]["post"]

    def test_request_is_multipart_only(self):
        content = self.upload_operation()["requestBody"]["content"]
        self.assertEqual(list(content), ["multipart/form-data"])

    def test_file_field_is_binary(self):
        schema = self.schema()
        content = self.upload_operation()["requestBody"]["content"]
        ref = content["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
        properties = schema["components"]["schemas"][ref]["properties"]
        self.assertEqual(properties["file"]["type"], "string")
        self.assertEqual(properties["file"]["format"], "binary")

    def test_base64_field_is_absent(self):
        schema = self.schema()
        content = self.upload_operation()["requestBody"]["content"]
        ref = content["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
        properties = schema["components"]["schemas"][ref]["properties"]
        self.assertNotIn("file_data", properties)

    def test_required_fields(self):
        schema = self.schema()
        content = self.upload_operation()["requestBody"]["content"]
        ref = content["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
        required = schema["components"]["schemas"][ref]["required"]
        self.assertIn("file", required)
        self.assertNotIn("original_name", required)
