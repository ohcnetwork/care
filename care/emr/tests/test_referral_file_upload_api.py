import base64
from unittest.mock import patch
from uuid import UUID, uuid4

from django.urls import reverse
from django.utils import timezone

from care.emr.models.consent import Consent
from care.emr.models.file_upload import FileUpload
from care.emr.models.patient import PatientUser
from care.emr.models.referral import Referral, ReferralAvailability, ReferralResource
from care.emr.utils.file_manager import S3FilesManager
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.security.permissions.referral import ReferralPermissions
from care.utils.tests.base import CareAPITestBase


class ReferralFileUploadAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.writer = self.create_user()
        self.reader = self.create_user()
        self.outsider = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.availability = ReferralAvailability.objects.create(
            entity_type="facility",
            facility=self.facility,
            name="Referral service",
            status="active",
            referral_type="consultation",
        )
        self.referral = self.make_referral()
        self.grant(
            self.user,
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
        )
        self.grant(self.writer, ReferralPermissions.can_write_referral.name)
        self.grant(self.reader, ReferralPermissions.can_read_referral.name)
        self.client.force_authenticate(user=self.user)
        self.signed_url = self.mock_storage("signed_url", "https://storage.test/upload")
        self.read_signed_url = self.mock_storage(
            "read_signed_url", "https://storage.test/download"
        )
        self.put_object = self.mock_storage("put_object", {})

    def mock_storage(self, method, return_value):
        patcher = patch.object(S3FilesManager, method, return_value=return_value)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def grant(self, user, *permissions, facility=None):
        role = self.create_role_with_permissions(permissions=list(permissions))
        return self.attach_role_facility_organization_user(
            (facility or self.facility).default_internal_organization, user, role
        )

    def make_referral(self, **kwargs):
        return Referral.objects.create(
            availability=kwargs.pop("availability", self.availability),
            patient=kwargs.pop("patient", self.patient),
            title="Clinical referral",
            **kwargs,
        )

    def upload_payload(self, **kwargs):
        return {
            "name": "Referral attachment",
            "original_name": "assessment.png",
            "file_type": "referral",
            "file_category": "unspecified",
            "associating_id": str(self.referral.external_id),
            "mime_type": "image/png",
            **kwargs,
        }

    def file_url(self, upload=None, action=None):
        if upload is None:
            return reverse("files-list")
        return reverse(
            f"files-{action or 'detail'}", kwargs={"external_id": upload.external_id}
        )

    def resource_url(self, referral=None, attachment=None, action=None):
        kwargs = {"referral_external_id": (referral or self.referral).external_id}
        if attachment is not None:
            kwargs["external_id"] = attachment.external_id
            return reverse(f"referral-resource-{action or 'detail'}", kwargs=kwargs)
        return reverse("referral-resource-list", kwargs=kwargs)

    def make_upload(self, referral=None, **kwargs):
        return FileUpload.objects.create(
            file_type="referral",
            associating_id=str((referral or self.referral).external_id),
            name="Assessment",
            internal_name="assessment.png",
            file_category="unspecified",
            meta={"mime_type": "image/png"},
            upload_completed=kwargs.pop("upload_completed", True),
            created_by=self.user,
            **kwargs,
        )

    def make_consent_upload(self, patient=None, **kwargs):
        encounter = self.create_encounter(
            patient=patient or self.patient,
            facility=self.facility,
            organization=self.facility.default_internal_organization,
        )
        consent = Consent.objects.create(
            encounter=encounter,
            status="active",
            category="treatment",
            date=timezone.now(),
            decision="permit",
        )
        return FileUpload.objects.create(
            file_type="consent",
            associating_id=str(consent.external_id),
            name="Consent attachment",
            internal_name="consent.pdf",
            file_category="consent_attachment",
            meta={"mime_type": "application/pdf"},
            upload_completed=kwargs.pop("upload_completed", True),
            created_by=self.user,
            **kwargs,
        )

    def list_files(self, **kwargs):
        return self.client.get(
            self.file_url(),
            {
                "file_type": "referral",
                "associating_id": str(self.referral.external_id),
                **kwargs,
            },
        )

    def attach(self, upload, **kwargs):
        return self.client.post(
            self.resource_url(),
            {
                "resource_type": "file_upload",
                "resource_id": str(upload.external_id),
                **kwargs,
            },
            format="json",
        )

    def test_referral_files_use_the_existing_signed_upload_lifecycle(self):
        created = self.client.post(
            self.file_url(), self.upload_payload(), format="json"
        )
        self.assertEqual(created.status_code, 200, created.data)
        self.assertEqual(created.data["signed_url"], "https://storage.test/upload")
        upload = FileUpload.objects.get(external_id=created.data["id"])
        self.assertEqual(upload.file_type, "referral")
        self.assertEqual(upload.associating_id, str(self.referral.external_id))
        self.assertEqual(upload.created_by_id, self.user.id)
        self.assertFalse(upload.upload_completed)
        self.assertIsNone(self.referral.encounter_id)
        self.assertEqual(self.list_files().data["count"], 0)

        completed = self.client.post(self.file_url(upload, "mark-upload-completed"))
        self.assertEqual(completed.status_code, 200, completed.data)
        upload.refresh_from_db()
        self.assertTrue(upload.upload_completed)
        listed = self.list_files()
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], str(upload.external_id))
        retrieved = self.client.get(self.file_url(upload))
        self.assertEqual(retrieved.status_code, 200, retrieved.data)
        self.assertEqual(
            retrieved.data["read_signed_url"], "https://storage.test/download"
        )

        renamed = self.client.patch(
            self.file_url(upload), {"name": "Updated assessment"}, format="json"
        )
        self.assertEqual(renamed.status_code, 200, renamed.data)
        archived = self.client.post(
            self.file_url(upload, "archive"),
            {"archive_reason": "Superseded assessment"},
            format="json",
        )
        self.assertEqual(archived.status_code, 200, archived.data)
        upload.refresh_from_db()
        self.assertEqual(upload.name, "Updated assessment")
        self.assertTrue(upload.is_archived)
        self.assertEqual(upload.archived_by_id, self.user.id)
        self.assertEqual(self.list_files(is_archived=False).data["count"], 0)

    def test_write_only_referral_access_can_complete_rename_and_archive_files(self):
        self.client.force_authenticate(user=self.writer)
        created = self.client.post(
            self.file_url(), self.upload_payload(), format="json"
        )
        self.assertEqual(created.status_code, 200, created.data)
        upload = FileUpload.objects.get(external_id=created.data["id"])
        self.assertEqual(self.list_files().status_code, 403)
        self.assertEqual(self.client.get(self.file_url(upload)).status_code, 403)
        completed = self.client.post(self.file_url(upload, "mark-upload-completed"))
        self.assertEqual(completed.status_code, 200, completed.data)
        renamed = self.client.put(
            self.file_url(upload), {"name": "Writer update"}, format="json"
        )
        self.assertEqual(renamed.status_code, 200, renamed.data)
        archived = self.client.post(
            self.file_url(upload, "archive"),
            {"archive_reason": "No longer needed"},
            format="json",
        )
        self.assertEqual(archived.status_code, 200, archived.data)

    def test_readers_can_read_files_but_cannot_upload_or_change_them(self):
        upload = self.make_upload()
        self.client.force_authenticate(user=self.reader)
        self.assertEqual(self.list_files().status_code, 200)
        self.assertEqual(self.client.get(self.file_url(upload)).status_code, 200)
        denied = self.client.post(self.file_url(), self.upload_payload(), format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        denied = self.client.patch(
            self.file_url(upload), {"name": "Not permitted"}, format="json"
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        for action, body in (
            ("mark-upload-completed", {}),
            ("archive", {"archive_reason": "Not permitted"}),
        ):
            denied = self.client.post(
                self.file_url(upload, action), body, format="json"
            )
            self.assertEqual(denied.status_code, 403, denied.data)
        upload.refresh_from_db()
        self.assertEqual(upload.name, "Assessment")
        self.assertFalse(upload.is_archived)

    def test_unrelated_users_cannot_access_or_change_referral_files(self):
        upload = self.make_upload()
        self.client.force_authenticate(user=self.outsider)
        self.assertEqual(self.list_files().status_code, 403)
        self.assertEqual(self.client.get(self.file_url(upload)).status_code, 403)
        denied = self.client.post(self.file_url(), self.upload_payload(), format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        denied = self.client.patch(
            self.file_url(upload), {"name": "Not permitted"}, format="json"
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        for action, body in (
            ("mark-upload-completed", {}),
            ("archive", {"archive_reason": "Not permitted"}),
        ):
            denied = self.client.post(
                self.file_url(upload, action), body, format="json"
            )
            self.assertEqual(denied.status_code, 403, denied.data)

    def test_missing_or_deleted_referrals_do_not_allow_file_access(self):
        missing = str(uuid4())
        denied = self.client.post(
            self.file_url(), self.upload_payload(associating_id=missing), format="json"
        )
        self.assertEqual(denied.status_code, 404, denied.data)
        upload = self.make_upload()
        self.referral.delete()
        self.assertEqual(self.list_files().status_code, 404)
        self.assertEqual(self.client.get(self.file_url(upload)).status_code, 404)
        denied = self.client.post(self.file_url(), self.upload_payload(), format="json")
        self.assertEqual(denied.status_code, 404, denied.data)

    def test_direct_upload_uses_the_same_referral_authorization(self):
        # A complete one-pixel PNG exercises MIME detection without external storage.
        file_data = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8A"
            "AwMCAO+aL1kAAAAASUVORK5CYII="
        )
        payload = {**self.upload_payload(), "file_data": file_data}
        self.client.force_authenticate(user=self.writer)
        created = self.client.post(reverse("files-upload-file"), payload, format="json")
        self.assertEqual(created.status_code, 200, created.data)
        upload = FileUpload.objects.get(external_id=created.data["id"])
        self.assertTrue(upload.upload_completed)
        self.assertEqual(upload.file_type, "referral")
        self.assertEqual(upload.created_by_id, self.writer.id)
        self.assertEqual(upload.updated_by_id, self.writer.id)
        self.assertEqual(
            created.data["read_signed_url"], "https://storage.test/download"
        )
        self.put_object.assert_called_once()
        stored_file = self.put_object.call_args.args[1]
        self.assertEqual(stored_file.read(), base64.b64decode(file_data))

        self.client.force_authenticate(user=self.outsider)
        denied = self.client.post(reverse("files-upload-file"), payload, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        self.put_object.assert_called_once()
        self.assertEqual(FileUpload.objects.count(), 1)

    def test_write_only_user_can_attach_own_referral_upload_and_reader_can_resolve_it(
        self,
    ):
        upload = self.make_upload()
        self.client.force_authenticate(user=self.writer)
        attached = self.attach(upload, attachment_type="response")
        self.assertEqual(attached.status_code, 200, attached.data)
        attachment = ReferralResource.objects.get(external_id=attached.data["id"])
        self.assertEqual(attachment.attachment_type, "response")
        self.client.force_authenticate(user=self.reader)
        resolved = self.client.get(
            self.resource_url(attachment=attachment, action="resolve")
        )
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.assertEqual(resolved.data["resource"]["id"], str(upload.external_id))
        self.assertEqual(
            resolved.data["resource"]["read_signed_url"],
            "https://storage.test/download",
        )
        upload.is_archived = True
        upload.save(update_fields=["is_archived"])
        unavailable = self.client.get(
            self.resource_url(attachment=attachment, action="resolve")
        )
        self.assertEqual(unavailable.status_code, 400, unavailable.data)

    def test_incomplete_archived_and_other_patient_files_cannot_be_attached(self):
        other_referral = self.make_referral(patient=self.create_patient())
        uploads = (
            self.make_upload(upload_completed=False),
            self.make_upload(is_archived=True),
            self.make_upload(referral=other_referral),
        )
        for upload in uploads:
            with self.subTest(upload=upload.external_id):
                denied = self.attach(upload)
                self.assertEqual(denied.status_code, 400, denied.data)
        self.assertFalse(ReferralResource.objects.exists())

    def test_patient_files_accept_equivalent_uuid_formats_when_attached_and_resolved(
        self,
    ):
        self.patient.external_id = UUID("d74f49f2-aaaa-4bbb-8ccc-dddddddddddd")
        self.patient.save(update_fields=["external_id"])
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_write_patient.name,
                PatientPermissions.can_view_clinical_data.name,
            ]
        )
        PatientUser.objects.create(patient=self.patient, user=self.user, role=role)
        for associating_id in (
            str(self.patient.external_id),
            str(self.patient.external_id).upper(),
            self.patient.external_id.hex,
        ):
            with self.subTest(associating_id=associating_id):
                self.client.force_authenticate(user=self.user)
                created = self.client.post(
                    self.file_url(),
                    self.upload_payload(
                        file_type="patient", associating_id=associating_id
                    ),
                    format="json",
                )
                self.assertEqual(created.status_code, 200, created.data)
                upload = FileUpload.objects.get(external_id=created.data["id"])
                self.assertEqual(upload.associating_id, associating_id)
                completed = self.client.post(
                    self.file_url(upload, "mark-upload-completed")
                )
                self.assertEqual(completed.status_code, 200, completed.data)
                self.assertEqual(
                    self.client.get(self.file_url(upload)).status_code, 200
                )
                attached = self.attach(upload)
                self.assertEqual(attached.status_code, 200, attached.data)
                attachment = ReferralResource.objects.get(
                    external_id=attached.data["id"]
                )

                self.client.force_authenticate(user=self.reader)
                self.assertEqual(
                    self.client.get(self.file_url(upload)).status_code, 403
                )
                resolved = self.client.get(
                    self.resource_url(attachment=attachment, action="resolve")
                )
                self.assertEqual(resolved.status_code, 200, resolved.data)
                self.assertEqual(
                    resolved.data["resource"]["id"], str(upload.external_id)
                )
                self.assertEqual(
                    resolved.data["resource"]["read_signed_url"],
                    "https://storage.test/download",
                )

    def test_invalid_and_other_patient_file_associations_cannot_be_attached(self):
        patient = self.create_patient(
            external_id=UUID("2b485f53-aaaa-4bbb-8ccc-dddddddddddd")
        )
        for associating_id in (
            str(patient.external_id),
            str(patient.external_id).upper(),
            patient.external_id.hex,
            "invalid-patient-id",
        ):
            with self.subTest(associating_id=associating_id):
                upload = FileUpload.objects.create(
                    file_type="patient",
                    associating_id=associating_id,
                    name="Other patient's assessment",
                    internal_name="assessment.png",
                    file_category="unspecified",
                    meta={"mime_type": "image/png"},
                    upload_completed=True,
                )
                denied = self.attach(upload)
                self.assertEqual(denied.status_code, 400, denied.data)
        self.assertFalse(ReferralResource.objects.exists())

    def test_other_referrals_files_require_source_access_and_matching_patient(self):
        source_facility = self.create_facility(user=self.outsider)
        source_availability = ReferralAvailability.objects.create(
            entity_type="facility",
            facility=source_facility,
            name="Other referral service",
            status="active",
            referral_type="consultation",
        )
        source_referral = self.make_referral(availability=source_availability)
        upload = self.make_upload(referral=source_referral)
        denied = self.attach(upload)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.grant(
            self.user,
            ReferralPermissions.can_read_referral.name,
            facility=source_facility,
        )
        attached = self.attach(upload)
        self.assertEqual(attached.status_code, 200, attached.data)
        attachment = ReferralResource.objects.get(external_id=attached.data["id"])
        self.client.force_authenticate(user=self.reader)
        resolved = self.client.get(
            self.resource_url(attachment=attachment, action="resolve")
        )
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.assertEqual(resolved.data["resource"]["id"], str(upload.external_id))

    def test_consent_files_require_source_read_access_and_allow_delegated_resolution(
        self,
    ):
        upload = self.make_consent_upload()
        denied = self.attach(upload)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertFalse(ReferralResource.objects.exists())

        self.grant(
            self.user, EncounterPermissions.can_read_encounter_clinical_data.name
        )
        attached = self.attach(upload)
        self.assertEqual(attached.status_code, 200, attached.data)
        attachment = ReferralResource.objects.get(external_id=attached.data["id"])
        self.assertEqual(attachment.resource_id, upload.external_id)

        self.client.force_authenticate(user=self.reader)
        self.assertEqual(self.client.get(self.file_url(upload)).status_code, 403)
        resolved = self.client.get(
            self.resource_url(attachment=attachment, action="resolve")
        )
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.assertEqual(resolved.data["resource"]["id"], str(upload.external_id))
        self.assertEqual(
            resolved.data["resource"]["read_signed_url"],
            "https://storage.test/download",
        )

    def test_unavailable_or_other_patient_consent_files_cannot_be_attached(self):
        self.grant(
            self.user, EncounterPermissions.can_read_encounter_clinical_data.name
        )
        missing_consent = self.make_consent_upload()
        missing_consent.associating_id = str(uuid4())
        missing_consent.save(update_fields=["associating_id"])
        deleted_consent = self.make_consent_upload()
        Consent.objects.get(external_id=deleted_consent.associating_id).delete()
        uploads = (
            self.make_consent_upload(upload_completed=False),
            self.make_consent_upload(is_archived=True),
            self.make_consent_upload(patient=self.create_patient()),
            missing_consent,
            deleted_consent,
        )
        for upload in uploads:
            with self.subTest(upload=upload.external_id):
                denied = self.attach(upload)
                self.assertEqual(denied.status_code, 400, denied.data)
        self.assertFalse(ReferralResource.objects.exists())
