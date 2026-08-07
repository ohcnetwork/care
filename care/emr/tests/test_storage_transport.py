"""
Provider-neutral transport tests (ADR-0001 / ES-01).

Asserts the property the architecture actually depends on: CARE mediates every
object transfer, so no storage-provider URL or endpoint ever reaches a client,
under either backend profile.
"""

import io
import uuid
import warnings

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse
from PIL import Image

from care.emr.models.file_upload import FileUpload
from care.emr.utils.file_manager import FilesManager, S3FilesManager
from care.utils.tests.base import CareAPITestBase

#: Substrings that would betray a storage-provider URL or endpoint in a response.
PROVIDER_URL_MARKERS = (
    "minio",
    "amazonaws",
    "s3.",
    "storage.googleapis",
    "googleapis.com",
    "X-Amz-Signature",
    "x-amz-signature",
    "GoogleAccessId",
    "Signature=",
    ":9100",
)


def assert_no_provider_url(testcase, payload):
    text = str(payload)
    for marker in PROVIDER_URL_MARKERS:
        testcase.assertNotIn(marker, text, f"provider URL marker {marker!r} leaked")


def response_content(response) -> bytes:
    return b"".join(response.streaming_content)


class NoProviderUrlInResponsesTests(CareAPITestBase):
    """Nothing CARE returns may contain a storage-provider URL."""

    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()

        # 800x800: the cover-image validator enforces a 400x400 / 1 KB minimum.
        self.file = io.BytesIO()
        Image.new("RGB", (800, 800)).save(self.file, format="JPEG")
        self.file.name = "scan.jpg"
        self.file.seek(0)

        self.client.force_authenticate(user=self.user)

    def _upload(self):
        return self.client.post(
            reverse("files-upload-file"),
            {
                "file": SimpleUploadedFile(
                    "scan.jpg", self.file.getvalue(), content_type="image/jpeg"
                ),
                "name": "scan",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
            },
            format="multipart",
        )

    def test_multipart_upload_works_and_returns_no_provider_url(self):
        response = self._upload()
        self.assertEqual(response.status_code, 200, response.data)
        assert_no_provider_url(self, response.data)

    def test_upload_response_offers_no_provider_upload_url(self):
        response = self._upload()
        self.assertNotIn("signed_url", response.data)
        self.assertNotIn("read_signed_url", response.data)

    def test_download_url_is_a_care_route(self):
        response = self._upload()
        self.assertEqual(
            response.data["download_url"],
            reverse("files-download", args=[response.data["id"]]),
        )

    def test_detail_and_list_responses_carry_no_provider_url(self):
        created = self._upload()
        detail = self.client.get(reverse("files-detail", args=[created.data["id"]]))
        self.assertEqual(detail.status_code, 200)
        assert_no_provider_url(self, detail.data)

        listing = self.client.get(
            reverse("files-list"),
            {"file_type": "patient", "associating_id": str(self.patient.external_id)},
        )
        self.assertEqual(listing.status_code, 200)
        assert_no_provider_url(self, listing.data)

    def test_download_through_django_returns_the_stored_bytes(self):
        created = self._upload()
        response = self.client.get(created.data["download_url"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_content(response), self.file.getvalue())

    def test_download_requires_authorization(self):
        created = self._upload()
        self.client.force_authenticate(user=self.create_user())
        response = self.client.get(created.data["download_url"])
        self.assertEqual(response.status_code, 403, response.content)

    def test_missing_object_yields_404_not_a_provider_error(self):
        created = self._upload()
        file_obj = FileUpload.objects.get(external_id=created.data["id"])
        file_obj.files_manager.delete_object(file_obj)
        response = self.client.get(created.data["download_url"])
        self.assertEqual(response.status_code, 404)

    def test_facility_cover_image_url_is_a_care_route(self):
        response = self.client.post(
            reverse("facility-cover-image", args=[self.facility.external_id]),
            {"cover_image": self.file},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.facility.refresh_from_db()
        url = self.facility.read_cover_image_url()
        self.assertEqual(
            url,
            reverse(
                "facility-cover-image-asset",
                kwargs={"external_id": self.facility.external_id},
            ),
        )
        assert_no_provider_url(self, url)

        served = self.client.get(url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(response_content(served), self.file.getvalue())

    def test_cover_image_is_served_without_authentication(self):
        # These objects were world-readable via the bucket; CARE now serves
        # them, but who can see them is unchanged.
        self.client.post(
            reverse("facility-cover-image", args=[self.facility.external_id]),
            {"cover_image": self.file},
            format="multipart",
        )
        self.facility.refresh_from_db()
        url = self.facility.read_cover_image_url()
        self.client.force_authenticate(user=None)
        served = self.client.get(url)
        self.assertEqual(served.status_code, 200)

    def test_avatar_url_is_a_care_route(self):
        response = self.client.post(
            reverse("users-profile-picture", args=[self.user.username]),
            {"profile_picture": self.file},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        url = self.user.read_profile_picture_url()
        self.assertEqual(
            url,
            reverse(
                "user-profile-picture-asset", kwargs={"username": self.user.username}
            ),
        )
        assert_no_provider_url(self, url)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_asset_route_404s_when_no_image_is_set(self):
        url = reverse(
            "facility-cover-image-asset",
            kwargs={"external_id": self.facility.external_id},
        )
        self.assertEqual(self.client.get(url).status_code, 404)


class ProviderNeutralPersistenceTests(SimpleTestCase):
    """Every alias round-trips through Django Storage under the s3 profile."""

    aliases = ("patient", "facility", "report")

    def test_all_aliases_round_trip(self):
        for alias in self.aliases:
            with self.subTest(alias=alias):
                storage = storages[alias]
                name = f"is01-transport/{uuid.uuid4()}.bin"
                try:
                    storage.save(name, ContentFile(b"payload"))
                    with storage.open(name, "rb") as handle:
                        self.assertEqual(handle.read(), b"payload")
                finally:
                    storage.delete(name)

    def test_no_alias_exposes_a_signed_url_helper(self):
        manager = FilesManager("patient")
        for attribute in ("signed_url", "read_signed_url", "generate_presigned_url"):
            self.assertFalse(hasattr(manager, attribute), attribute)


class PluginCompatibilityTests(SimpleTestCase):
    """S3FilesManager stays importable for plugins, minus the signed URLs."""

    def test_importable_and_deprecated(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            manager = S3FilesManager("PATIENT")
        self.assertTrue(
            any(issubclass(w.category, DeprecationWarning) for w in caught),
            "expected a DeprecationWarning",
        )
        self.assertIsInstance(manager, FilesManager)

    def test_delegates_to_django_storage(self):
        manager = S3FilesManager("PATIENT")
        self.assertEqual(manager.storage_alias, "patient")
        self.assertIs(type(manager.storage), type(storages["patient"]))

    def test_accepts_each_legacy_bucket_name(self):
        for legacy, alias in (
            ("PATIENT", "patient"),
            ("FACILITY", "facility"),
            ("REPORT", "report"),
        ):
            with self.subTest(legacy=legacy):
                self.assertEqual(S3FilesManager(legacy).storage_alias, alias)

    def test_rejects_unknown_alias(self):
        with self.assertRaises(ValueError):
            S3FilesManager("does-not-exist")

    def test_exposes_no_signed_url_methods(self):
        manager = S3FilesManager("PATIENT")
        for attribute in ("signed_url", "read_signed_url", "generate_presigned_url"):
            self.assertFalse(hasattr(manager, attribute), attribute)
