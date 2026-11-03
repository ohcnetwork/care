import uuid
from datetime import timedelta
from unittest.mock import patch

import requests
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports import report_utils
from care.emr.signals.patient.facility_name_identifier import (
    FacilityPatientNameIdentifierConfig,
)
from care.emr.signals.patient.name_identifier import NameIdentifierConfig
from care.emr.signals.patient.phone_number_identifier import PhoneNumberIdentifierConfig
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.template import TemplatePermissions
from care.utils.tests.base import CareAPITestBase


@override_settings(
    FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT=settings.BUCKET_ENDPOINT,
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class ReportUploadAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        # Cached identifier rows are rolled back between tests.
        for config in (
            NameIdentifierConfig,
            PhoneNumberIdentifierConfig,
            FacilityPatientNameIdentifierConfig,
        ):
            config_patcher = patch.object(config, "CACHED_CONFIG", {})
            config_patcher.start()
            self.addCleanup(config_patcher.stop)
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.patient = self.create_patient(name="Report Test Patient")
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.template = self.create_report_template()
        self.lock_key = report_utils.get_lock_key(
            self.template.template_type, str(self.encounter.external_id)
        )
        report_utils.clear_lock(self.lock_key)
        self.addCleanup(report_utils.clear_lock, self.lock_key)

        self.client.force_authenticate(user=self.superuser)

    def get_url(self):
        return reverse("template-reports-list")

    def get_detail_url(self, report_id):
        return reverse("template-reports-detail", args=[report_id])

    def get_generate_url(self):
        return reverse("template-reports-generate")

    def get_archive_url(self, report_id):
        return reverse("template-reports-archive", args=[report_id])

    def create_report_template(self, facility=None, **kwargs):
        slug_value = f"report-{uuid.uuid4()}"
        data = {
            "name": "Test Report Template",
            "slug": (
                f"f-{facility.external_id}-{slug_value}"
                if facility
                else f"i-{slug_value}"
            ),
            "facility": facility,
            "status": "active",
            "template_type": "discharge_summary",
            "default_format": "html",
            "context": "encounter_base",
            "template_data": (
                "<!DOCTYPE html>"
                '<html><head><meta charset="UTF-8" /></head>'
                "<body><h1>Discharge Summary</h1>"
                "<p>{{ encounter.patient.name }}</p>"
                "</body></html>"
            ),
        }
        data.update(kwargs)
        return baker.make(Template, **data)

    def create_report_upload(self, **kwargs):
        data = {
            "template": self.template,
            "name": "Test Discharge Summary",
            "internal_name": "report.html",
            "associating_id": str(self.encounter.external_id),
            "report_type": "discharge_summary",
            "upload_completed": True,
            "created_by": self.superuser,
            "meta": {"mime_type": "text/html"},
        }
        data.update(kwargs)
        return baker.make(ReportUpload, **data)

    def generate_report_data(self, **kwargs):
        return {
            "template_id": str(self.template.external_id),
            "associating_id": str(self.encounter.external_id),
            **kwargs,
        }

    def list_report_data(self, **kwargs):
        return {
            "report_type": "discharge_summary",
            "associating_id": str(self.encounter.external_id),
            **kwargs,
        }

    def create_user_with_permissions(self, permissions, organization=None):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[permission.name for permission in permissions]
        )
        self.attach_role_facility_organization_user(
            organization or self.facility_organization, user, role
        )
        return user

    def assert_generation_started(self, response, output_format="html", user=None):
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.content, b"")
        report = ReportUpload.objects.get(
            template=self.template,
            report_type=self.template.template_type,
            associating_id=str(self.encounter.external_id),
        )
        self.assertEqual(report.created_by, user or self.superuser)
        self.assertEqual(report.meta["output_format"], output_format)
        self.assertTrue(report.upload_completed)
        mime_type, content = report.files_manager.file_contents(report)
        self.assertEqual(mime_type, report.meta["mime_type"])
        self.assertGreater(len(content), 0)

    def tearDown(self):
        try:
            for report in ReportUpload.objects.filter(
                associating_id=str(self.encounter.external_id),
                meta__has_key="generated_at",
            ):
                report.files_manager.delete_object(report)
        finally:
            super().tearDown()

    def generate_uploaded_report(self, output_format="html", **kwargs):
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(output_format=output_format, **kwargs),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.content, b"")
        report = ReportUpload.objects.filter(
            template=self.template,
            associating_id=str(self.encounter.external_id),
        ).latest("id")
        self.assertTrue(report.upload_completed)
        self.assertEqual(report.created_by, self.superuser)
        self.assertEqual(report.report_type, self.template.template_type)
        self.assertEqual(report.meta["output_format"], output_format)
        self.assertIsNone(report_utils.get_progress(self.lock_key))
        return report

    def fetch_report(self, report):
        response = self.client.get(self.get_detail_url(report.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(report.external_id))
        self.assertTrue(response.data["upload_completed"])
        self.assertTrue(response.data["read_signed_url"])
        file_response = requests.get(response.data["read_signed_url"], timeout=10)
        self.assertEqual(file_response.status_code, 200, file_response.text)
        self.assertEqual(
            file_response.headers["Content-Type"], report.meta["mime_type"]
        )
        stored_type, stored_content = report.files_manager.file_contents(report)
        self.assertEqual(stored_type, report.meta["mime_type"])
        self.assertEqual(file_response.content, stored_content)
        return response, file_response

    def generate_and_fetch_report(self, output_format="html", **kwargs):
        report = self.generate_uploaded_report(output_format=output_format, **kwargs)
        _, file_response = self.fetch_report(report)
        return report, file_response

    # List report uploads

    def test_list_report_uploads_as_superuser(self):
        """Verify a superuser can list reports with the expected public fields."""
        report = self.create_report_upload()
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        data = response.data["results"][0]
        self.assertEqual(data["id"], str(report.external_id))
        self.assertEqual(data["name"], report.name)
        self.assertEqual(data["report_type"], report.report_type)
        self.assertEqual(data["associating_id"], report.associating_id)
        self.assertEqual(data["template"]["id"], str(self.template.external_id))
        self.assertEqual(data["extension"], ".html")
        self.assertEqual(data["mime_type"], "text/html")
        self.assertTrue(data["upload_completed"])
        self.assertFalse(data["is_archived"])
        self.assertNotIn("read_signed_url", data)
        self.assertNotIn("internal_name", data)

    def test_list_report_uploads_with_read_permission(self):
        """Verify encounter read permission allows listing associated reports."""
        report = self.create_report_upload()
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_read_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], str(report.external_id))

    def test_list_report_uploads_without_permission(self):
        """Verify users without report read access receive a permission error."""
        self.create_report_upload()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot read report of type discharge_summary"
        )

    def test_list_report_uploads_unauthenticated(self):
        """Verify listing reports requires authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Authentication credentials were not provided."
        )

    def test_list_report_uploads_with_missing_required_filters(self):
        """Verify listing requires both report type and associating ID."""
        for data in (
            {},
            {"report_type": "discharge_summary"},
            {"associating_id": str(self.encounter.external_id)},
        ):
            with self.subTest(data=data):
                response = self.client.get(self.get_url(), data)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.data["detail"],
                    "report_type and associating_id are required",
                )

    def test_list_report_uploads_with_invalid_report_type(self):
        """Verify listing rejects an unregistered report type."""
        response = self.client.get(
            self.get_url(), self.list_report_data(report_type="invalid_type")
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Invalid report type: invalid_type")

    def test_list_report_uploads_with_nonexistent_encounter(self):
        """Verify listing reports for a nonexistent encounter returns not found."""
        response = self.client.get(
            self.get_url(), self.list_report_data(associating_id=str(uuid.uuid4()))
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No Encounter matches the given query.",
        )

    def test_list_report_uploads_isolates_report_type_and_encounter(self):
        """Verify listing excludes other report types and encounters."""
        report = self.create_report_upload()
        self.create_report_upload(report_type="encounter")
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.create_report_upload(associating_id=str(other_encounter.external_id))
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(report.external_id)],
        )

    def test_list_report_uploads_with_no_reports(self):
        """Verify an encounter without reports returns an empty paginated list."""
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_list_report_uploads_filtered_by_name(self):
        """Verify the name filter matches report names case-insensitively."""
        report = self.create_report_upload(name="Discharge Summary")
        self.create_report_upload(name="Other report")
        response = self.client.get(
            self.get_url(), self.list_report_data(name="DISCHARGE")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(report.external_id)],
        )

    def test_list_report_uploads_filtered_by_template(self):
        """Verify the template filter matches the exact template slug."""
        report = self.create_report_upload()
        self.create_report_upload(template=self.create_report_template())
        response = self.client.get(
            self.get_url(), self.list_report_data(template=self.template.slug)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(report.external_id)],
        )

    def test_list_report_uploads_filtered_by_archive_status(self):
        """Verify the archive filter selects archived or active reports."""
        active = self.create_report_upload()
        archived = self.create_report_upload(is_archived=True)
        for value, report in (("true", archived), ("false", active)):
            with self.subTest(is_archived=value):
                response = self.client.get(
                    self.get_url(), self.list_report_data(is_archived=value)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [str(report.external_id)],
                )

    def test_list_report_uploads_filtered_by_upload_completion(self):
        """Verify the completion filter selects completed or pending uploads."""
        completed = self.create_report_upload()
        pending = self.create_report_upload(upload_completed=False)
        for value, report in (("true", completed), ("false", pending)):
            with self.subTest(upload_completed=value):
                response = self.client.get(
                    self.get_url(), self.list_report_data(upload_completed=value)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [str(report.external_id)],
                )

    def test_list_report_uploads_ordered_by_name(self):
        """Verify report names support ascending and descending ordering."""
        alpha = self.create_report_upload(name="Alpha")
        beta = self.create_report_upload(name="Beta")
        for ordering, expected in (
            ("name", [alpha, beta]),
            ("-name", [beta, alpha]),
        ):
            with self.subTest(ordering=ordering):
                response = self.client.get(
                    self.get_url(), self.list_report_data(ordering=ordering)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [str(report.external_id) for report in expected],
                )

    def test_list_report_uploads_ordered_by_created_date(self):
        """Verify creation dates support ascending and descending ordering."""
        older = self.create_report_upload()
        newer = self.create_report_upload()
        ReportUpload.objects.filter(pk=older.pk).update(
            created_date=timezone.now() - timedelta(days=1)
        )
        for ordering, expected in (
            ("created_date", [older, newer]),
            ("-created_date", [newer, older]),
        ):
            with self.subTest(ordering=ordering):
                response = self.client.get(
                    self.get_url(), self.list_report_data(ordering=ordering)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [str(report.external_id) for report in expected],
                )

    # Retrieve generated report uploads

    def test_retrieve_report_upload_as_superuser(self):
        """Verify a generated report has real details and a working download URL."""
        report = self.generate_uploaded_report()
        response, file_response = self.fetch_report(report)
        self.assertEqual(response.data["internal_name"], report.internal_name)
        self.assertIsNone(response.data["signed_url"])
        self.assertEqual(response.data["template"]["slug"], self.template.slug)
        self.assertIn("<p>Report Test Patient</p>", file_response.text)
        self.assertEqual(file_response.headers["Content-Type"], "text/html")
        self.assertEqual(
            file_response.headers["Content-Disposition"],
            f"attachment; filename={report.name}.html",
        )

    def test_retrieve_report_upload_with_read_permission(self):
        """Verify encounter read access retrieves and downloads a generated report."""
        report = self.generate_uploaded_report()
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_read_encounter]
        )
        self.client.force_authenticate(user=user)
        _, file_response = self.fetch_report(report)
        self.assertIn("<p>Report Test Patient</p>", file_response.text)

    def test_retrieve_report_upload_without_permission(self):
        """Verify unauthorized retrieval does not expose a generated report URL."""
        report = self.generate_uploaded_report()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_detail_url(report.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot read report of type discharge_summary"
        )
        self.assertNotIn("read_signed_url", response.data)

    def test_retrieve_report_upload_unauthenticated(self):
        """Verify unauthenticated users cannot retrieve a generated report."""
        report = self.generate_uploaded_report()
        self.client.force_authenticate(user=None)
        response = self.client.get(self.get_detail_url(report.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("read_signed_url", response.data)
        self.assertEqual(
            response.data["detail"], "Authentication credentials were not provided."
        )

    def test_retrieve_nonexistent_report_upload(self):
        """Verify retrieving a nonexistent report returns not found."""
        response = self.client.get(self.get_detail_url(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No ReportUpload matches the given query.",
        )

    def test_retrieve_report_upload_from_another_facility_is_denied(self):
        """Verify another facility's read permission cannot retrieve the report."""
        report = self.generate_uploaded_report()
        other_facility = self.create_facility(user=self.superuser)
        other_organization = self.create_facility_organization(
            facility=other_facility, org_type="root"
        )
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_read_encounter], other_organization
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.get_detail_url(report.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("read_signed_url", response.data)
        self.assertEqual(
            response.data["detail"], "Cannot read report of type discharge_summary"
        )

    def test_generate_and_download_html_report(self):
        """Verify real HTML generation, storage, download headers and rendered data."""
        report, file_response = self.generate_and_fetch_report()
        self.assertEqual(report.get_extension(), ".html")
        self.assertEqual(file_response.headers["Content-Type"], "text/html")
        self.assertIn("<h1>Discharge Summary</h1>", file_response.text)
        self.assertIn("<p>Report Test Patient</p>", file_response.text)
        self.assertNotIn("{{", file_response.text)
        self.assertEqual(
            file_response.headers["Content-Disposition"],
            f"attachment; filename={report.name}.html",
        )
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(report.external_id)],
        )

    def test_generate_and_download_pdf_report(self):
        """Verify real PDF generation and download preserve bytes and PDF headers."""
        report, file_response = self.generate_and_fetch_report(output_format="pdf")
        self.assertEqual(report.get_extension(), ".pdf")
        self.assertEqual(file_response.headers["Content-Type"], "application/pdf")
        self.assertTrue(file_response.content.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", file_response.content)
        self.assertEqual(
            file_response.headers["Content-Disposition"],
            f"inline; filename={report.name}.pdf",
        )

    def test_archive_generated_report_preserves_download(self):
        """Verify archived reports remain downloadable with their original content."""
        report, original_file = self.generate_and_fetch_report()
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Replaced by a new report"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        report.refresh_from_db()
        self.assertTrue(report.is_archived)
        self.assertEqual(report.archived_by, self.superuser)
        response = self.client.get(self.get_detail_url(report.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_archived"])
        downloaded = requests.get(response.data["read_signed_url"], timeout=10)
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(downloaded.content, original_file.content)
        response = self.client.get(
            self.get_url(), self.list_report_data(is_archived="false")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_force_regenerate_report_creates_independent_files(self):
        """Verify forced regeneration stores a new file without altering the original."""
        original, original_file = self.generate_and_fetch_report()
        self.template.template_data = "<h1>Updated Discharge Summary</h1>"
        self.template.save(update_fields=["template_data"])
        report_utils.set_lock(self.lock_key, 50)
        replacement, replacement_file = self.generate_and_fetch_report(force=True)
        self.assertNotEqual(original.external_id, replacement.external_id)
        self.assertNotEqual(original.internal_name, replacement.internal_name)
        self.assertEqual(
            replacement_file.content, b"<h1>Updated Discharge Summary</h1>"
        )
        self.assertEqual(
            original.files_manager.file_contents(original)[1], original_file.content
        )
        response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    # Generate reports

    def test_generate_report_as_superuser(self):
        """Verify generation creates one report listed for its associated encounter."""
        report = self.generate_uploaded_report()
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.create_report_upload(associating_id=str(other_encounter.external_id))

        get_response = self.client.get(self.get_url(), self.list_report_data())
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["count"], 1)
        self.assertEqual(len(get_response.data["results"]), 1)
        self.assertEqual(get_response.data["results"][0]["id"], str(report.external_id))
        self.assertEqual(
            get_response.data["results"][0]["associating_id"],
            str(self.encounter.external_id),
        )

    def test_generate_report_from_facility_template_with_permissions(self):
        """Verify encounter and facility template permissions allow generation."""
        self.template = self.create_report_template(facility=self.facility)
        user = self.create_user_with_permissions(
            [
                EncounterPermissions.can_write_encounter,
                TemplatePermissions.can_generate_report_from_template,
            ]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assert_generation_started(response, user=user)

    def test_generate_global_report_with_encounter_write_permission(self):
        """Verify global templates require only encounter write permission."""
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_write_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assert_generation_started(response, user=user)

    def test_generate_report_without_encounter_permission(self):
        """Verify generation without encounter write access is not enqueued."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot write report of type discharge_summary"
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_without_template_permission(self):
        """Verify facility templates require template generation permission."""
        self.template = self.create_report_template(facility=self.facility)
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_write_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You are not authorized to generate reports"
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_only_template_permission(self):
        """Verify template permission alone cannot bypass encounter access."""
        self.template = self.create_report_template(facility=self.facility)
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_generate_report_from_template]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot write report of type discharge_summary"
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_unauthenticated(self):
        """Verify unauthenticated requests cannot enqueue report generation."""
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Authentication credentials were not provided."
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_missing_required_fields(self):
        """Verify generation reports missing template or associating IDs."""
        for field in ("template_id", "associating_id"):
            with self.subTest(field=field):
                data = self.generate_report_data()
                del data[field]
                response = self.client.post(
                    self.get_generate_url(), data, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["errors"][0]["loc"], [field])
                self.assertEqual(response.data["errors"][0]["type"], "missing")
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_invalid_uuids(self):
        """Verify generation IDs must be valid version-four UUIDs."""
        for field in ("template_id", "associating_id"):
            for value in ("invalid-uuid", str(uuid.uuid1())):
                with self.subTest(field=field, value=value):
                    response = self.client.post(
                        self.get_generate_url(),
                        self.generate_report_data(**{field: value}),
                        format="json",
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.data["errors"][0]["loc"], [field])
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_nonexistent_template(self):
        """Verify generation with a nonexistent template returns not found."""
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(template_id=str(uuid.uuid4())),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No Template matches the given query.",
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_nonexistent_encounter(self):
        """Verify generation with a nonexistent encounter is not enqueued."""
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(associating_id=str(uuid.uuid4())),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_inactive_template(self):
        """Verify draft and retired templates cannot generate reports."""
        for template_status in ("draft", "retired"):
            with self.subTest(status=template_status):
                self.template.status = template_status
                self.template.save(update_fields=["status"])
                response = self.client.post(
                    self.get_generate_url(),
                    self.generate_report_data(),
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"][0]["msg"], "Template is not active"
                )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_invalid_output_format(self):
        """Verify generation rejects unsupported output formats."""
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(output_format="docx"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["errors"][0]["loc"], ["output_format"])
        self.assertIn("Invalid output format", response.data["errors"][0]["msg"])
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_with_explicit_output_format(self):
        """Verify an explicit PDF format overrides the template default."""
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(output_format="pdf"),
            format="json",
        )
        self.assert_generation_started(response, output_format="pdf")

    def test_generate_report_with_null_output_format_uses_default(self):
        """Verify a null output format falls back to the template default."""
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(output_format=None),
            format="json",
        )
        self.assert_generation_started(response)

    def test_generate_report_for_completed_encounter_without_permission(self):
        """Verify completed encounters require their dedicated permission."""
        self.encounter.status = "completed"
        self.encounter.save(update_fields=["status"])
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_write_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot write report of type discharge_summary"
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_for_completed_encounter_with_permission(self):
        """Verify the dedicated permission allows completed encounter reports."""
        self.encounter.status = "completed"
        self.encounter.save(update_fields=["status"])
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_generate_report_for_completed_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assert_generation_started(response, user=user)

    def test_generate_report_already_in_progress(self):
        """Verify existing progress prevents duplicate generation with a conflict."""
        report_utils.set_lock(self.lock_key, 50)
        response = self.client.post(
            self.get_generate_url(), self.generate_report_data(), format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Report generation is already in progress for this report, "
            "current progress 50%",
        )
        self.assertEqual(report_utils.get_progress(self.lock_key), 50)
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_force_generate_report_clears_progress(self):
        """Verify forced generation clears existing progress and enqueues a task."""
        report_utils.set_lock(self.lock_key, 50)
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(force=True),
            format="json",
        )
        self.assert_generation_started(response)
        self.assertIsNone(report_utils.get_progress(self.lock_key))

    def test_force_generate_report_without_permission_preserves_progress(self):
        """Verify unauthorized forced generation leaves the progress lock intact."""
        report_utils.set_lock(self.lock_key, 50)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(force=True),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(report_utils.get_progress(self.lock_key), 50)
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_status_check_with_progress(self):
        """Verify status checks return current progress without enqueueing a task."""
        report_utils.set_lock(self.lock_key, 75)
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(status_check=True),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"progress": 75})
        self.assertEqual(report_utils.get_progress(self.lock_key), 75)
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_status_check_without_progress(self):
        """Verify status checks without progress return an empty response."""
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(status_check=True),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {})
        self.assertEqual(ReportUpload.objects.count(), 0)

    def test_generate_report_status_check_requires_permission(self):
        """Verify generation status is not exposed to unauthorized users."""
        report_utils.set_lock(self.lock_key, 75)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_generate_url(),
            self.generate_report_data(status_check=True),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot write report of type discharge_summary"
        )
        self.assertEqual(ReportUpload.objects.count(), 0)

    # Archive report uploads

    def test_archive_report_upload_as_superuser(self):
        """Verify archiving persists audit metadata and updates list responses."""
        report = self.create_report_upload()
        internal_name = report.internal_name
        before = timezone.now()
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Replaced by an updated report"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        report.refresh_from_db()
        self.assertTrue(report.is_archived)
        self.assertEqual(report.archive_reason, "Replaced by an updated report")
        self.assertEqual(report.archived_by, self.superuser)
        self.assertGreaterEqual(report.archived_datetime, before)
        self.assertLessEqual(report.archived_datetime, timezone.now())
        self.assertEqual(response.data["id"], str(report.external_id))
        self.assertTrue(response.data["is_archived"])
        self.assertEqual(response.data["archive_reason"], report.archive_reason)
        self.assertIsNotNone(response.data["archived_datetime"])
        listed = self.client.get(
            self.get_url(), self.list_report_data(is_archived="true")
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            listed.data["results"][0]["archive_reason"], report.archive_reason
        )
        self.assertEqual(report.internal_name, internal_name)
        self.assertTrue(report.upload_completed)
        self.assertNotIn("internal_name", response.data)

    def test_archive_report_upload_with_write_permission(self):
        """Verify encounter write permission allows archiving its reports."""
        report = self.create_report_upload()
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_write_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Incorrect report"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertTrue(report.is_archived)
        self.assertEqual(report.archived_by, user)

    def test_archive_report_upload_without_permission(self):
        """Verify denied archive requests leave report metadata unchanged."""
        report = self.create_report_upload()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Incorrect report"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot write report of type discharge_summary"
        )
        report.refresh_from_db()
        self.assertFalse(report.is_archived)
        self.assertEqual(report.archive_reason, "")
        self.assertIsNone(report.archived_by)
        self.assertIsNone(report.archived_datetime)

    def test_archive_report_upload_with_only_read_permission(self):
        """Verify read permission alone does not allow archiving reports."""
        report = self.create_report_upload()
        user = self.create_user_with_permissions(
            [EncounterPermissions.can_read_encounter]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Incorrect report"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Cannot write report of type discharge_summary"
        )
        report.refresh_from_db()
        self.assertFalse(report.is_archived)
        self.assertEqual(report.archive_reason, "")
        self.assertIsNone(report.archived_by)
        self.assertIsNone(report.archived_datetime)

    def test_archive_report_upload_unauthenticated(self):
        """Verify unauthenticated archive requests leave the report active."""
        report = self.create_report_upload()
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Incorrect report"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        report.refresh_from_db()
        self.assertFalse(report.is_archived)
        self.assertEqual(report.archive_reason, "")
        self.assertIsNone(report.archived_by)
        self.assertIsNone(report.archived_datetime)

    def test_archive_nonexistent_report_upload(self):
        """Verify archiving a nonexistent report returns not found."""
        response = self.client.post(
            self.get_archive_url(uuid.uuid4()),
            {"archive_reason": "Incorrect report"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No ReportUpload matches the given query.",
        )

    def test_archive_report_upload_with_missing_reason(self):
        """Verify archiving requires an archive reason field."""
        report = self.create_report_upload()
        response = self.client.post(
            self.get_archive_url(report.external_id), {}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["errors"][0]["loc"], ["archive_reason"])
        report.refresh_from_db()
        self.assertFalse(report.is_archived)

    def test_archive_report_upload_with_invalid_reason(self):
        """Verify archive reasons must be strings and invalid values change nothing."""
        report = self.create_report_upload()
        for reason in (None, 123, []):
            with self.subTest(reason=reason):
                response = self.client.post(
                    self.get_archive_url(report.external_id),
                    {"archive_reason": reason},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["errors"][0]["loc"], ["archive_reason"])
                report.refresh_from_db()
                self.assertFalse(report.is_archived)

    def test_archive_report_upload_with_empty_reason(self):
        """Verify the current archive contract accepts an empty reason string."""
        report = self.create_report_upload()
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertTrue(report.is_archived)
        self.assertEqual(report.archive_reason, "")

    def test_archive_report_upload_again_updates_metadata(self):
        """Verify rearchiving updates the reason, archiver and archive timestamp."""
        report = self.create_report_upload(
            is_archived=True,
            archive_reason="Old reason",
            archived_by=self.user,
            archived_datetime=timezone.now() - timedelta(days=1),
        )
        response = self.client.post(
            self.get_archive_url(report.external_id),
            {"archive_reason": "Updated reason"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertTrue(report.is_archived)
        self.assertEqual(report.archive_reason, "Updated reason")
        self.assertEqual(report.archived_by, self.superuser)
        self.assertGreater(
            report.archived_datetime, timezone.now() - timedelta(minutes=1)
        )
