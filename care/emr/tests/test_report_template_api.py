import uuid
from unittest.mock import patch

from django.urls import reverse
from model_bakery import baker

from care.emr.models.report.template import Template
from care.security.permissions.template import TemplatePermissions
from care.utils.tests.base import CareAPITestBase


class ReportTemplateAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facilty = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facilty, org_type="root"
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                TemplatePermissions.can_write_template.name,
                TemplatePermissions.can_read_template.name,
            ]
        )

    def get_url(self):
        return reverse("template-list")

    def get_detail_url(self, slug):
        return reverse("template-detail", kwargs={"slug": slug})

    def generate_report_template_data(self, facility):
        return {
            "name": "Test Report Template",
            "slug_value": "test-report-template",
            "default_format": "html",
            "status": "active",
            "template_type": "discharge_summary",
            "facility": facility,
            "template_data": (
                "<!DOCTYPE html>\n"
                "<html>\n"
                '<head><meta charset="UTF-8" /></head>\n'
                "<body>\n"
                "  <h1>{{ encounter.facility.name }}</h1>\n"
                "  <h2>Discharge Summary</h2>\n"
                "  <p>Name: {{ encounter.patient.name }}</p>\n"
                "  <p>Age: {{ encounter.patient.age }}</p>\n"
                "  <p>Gender: {{ encounter.patient.gender }}</p>\n"
                "  <p>Admission: {{ encounter.start_time | datetime }}</p>\n"
                "</body>\n"
                "</html>"
            ),
            "context": "encounter_base",
        }

    def get_schema_url(self):
        return reverse("template-get-schema")

    def get_preview_url(self):
        return reverse("template-preview")

    def create_report_template(
        self, facility=None, slug="test-report-template", **kwargs
    ):
        data = self.generate_report_template_data(facility=None)
        data.pop("slug_value")
        data.pop("facility")
        data.update(kwargs)
        return baker.make(
            "emr.Template",
            **data,
            facility=facility,
            slug=f"f-{facility.external_id}-{slug}" if facility else f"i-{slug}",
        )

    def generate_preview_data(self, **kwargs):
        data = self.generate_report_template_data(facility=None)
        return {
            "template_data": data["template_data"],
            "output_format": "html",
            "context": "encounter_base",
            "options": {},
            **kwargs,
        }

    def create_user_with_permissions(self, permissions, facility_organization=None):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[permission.name for permission in permissions]
        )
        self.attach_role_facility_organization_user(
            facility_organization or self.facility_organization, user, role
        )
        return user

    # Test cases for create report template

    def test_create_report_template_as_superuser(self):
        """
        Test creating a report template as a superuser.
        """
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_report_template_as_regular_user_without_permission(self):
        """
        Test creating a report template as a regular user.
        """
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write templates"
        )

    def test_create_report_template_as_user_with_permission(self):
        """
        Test creating a report template as a regular user with write permission.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_report_template_response_data(self):
        """Test the response data and audit fields of a created report template"""
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["slug"], f"f-{self.facilty.external_id}-test-report-template"
        )
        self.assertEqual(
            response.data["slug_config"],
            {
                "facility": str(self.facilty.external_id),
                "slug_value": "test-report-template",
            },
        )
        self.assertEqual(response.data["facility"]["id"], str(self.facilty.external_id))
        self.assertEqual(response.data["template_data"], data["template_data"])
        template = Template.objects.get(external_id=response.data["id"])
        self.assertEqual(template.created_by, self.superuser)
        self.assertEqual(template.updated_by, self.superuser)

    def test_create_report_template_as_user_with_read_permission_only(self):
        """Test creating a report template as a user with only read permission"""
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_read_template]
        )
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=user)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write templates"
        )

    def test_create_report_template_as_user_in_non_root_organization(self):
        """Test creating a report template with write permission in a non-root organization"""
        team_organization = self.create_facility_organization(
            facility=self.facilty, org_type="team"
        )
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_write_template], team_organization
        )
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=user)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write templates"
        )

    def test_create_report_template_unauthenticated(self):
        """Test creating a report template without authentication"""
        data = self.generate_report_template_data(self.facilty.external_id)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "Authentication credentials were not provided."
        )

    def test_create_global_report_template_as_superuser(self):
        """Test creating an instance level report template as a superuser"""
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "i-test-report-template")
        self.assertIsNone(response.data["facility"])

    def test_create_global_report_template_as_user_with_permission(self):
        """Test creating an instance level report template as a non superuser"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write templates"
        )

    def test_create_report_template_with_invalid_facility(self):
        """Test creating a report template with a facility that does not exist"""
        data = self.generate_report_template_data(str(uuid.uuid4()))
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"], "No Facility matches the given query."
        )

    def test_create_report_template_with_duplicate_slug(self):
        """Test creating a facility report template with an existing slug"""
        self.create_report_template(facility=self.facilty)
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Slug already exists.", str(response.data))

    def test_create_global_report_template_with_duplicate_slug(self):
        """Test creating an instance level report template with an existing slug"""
        self.create_report_template()
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Slug already exists.", str(response.data))

    def test_create_report_template_with_slug_used_by_global_template(self):
        """Test the same slug can be used at facility and instance level"""
        self.create_report_template()
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_report_template_with_empty_template_type(self):
        """Test creating a report template with an empty template type"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["template_type"] = ""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Report Type is required", str(response.data))

    def test_create_report_template_with_invalid_template_type(self):
        """Test creating a report template with an unregistered template type"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["template_type"] = "invalid_type"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid report type", str(response.data))

    def test_create_report_template_with_empty_context(self):
        """Test creating a report template with an empty context"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["context"] = ""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Report Type is required", str(response.data))

    def test_create_report_template_with_invalid_context(self):
        """Test creating a report template with an unregistered context"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["context"] = "invalid_context"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid report type or context", str(response.data))

    def test_create_report_template_when_context_lookup_fails(self):
        """Test creating a report template when the context registry lookup raises"""
        data = self.generate_report_template_data(self.facilty.external_id)
        self.client.force_authenticate(user=self.superuser)
        with patch(
            "care.emr.resources.report.template.spec.DataPointRegistry.get",
            side_effect=KeyError("encounter_base"),
        ):
            response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid Context type", str(response.data))

    def test_create_report_template_with_incompatible_context(self):
        """Test creating a report template whose type and context do not match"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["template_type"] = "patient_summary"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Report Type and Context are not compatible", str(response.data))

    def test_create_report_template_with_patient_context(self):
        """Test creating a patient summary report template"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["template_type"] = "patient_summary"
        data["context"] = "patient_base"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_report_template_with_valid_options(self):
        """Test creating a report template with valid generator options"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["options"] = {"wrap_document": True, "title": "My Report"}
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["options"]["title"], "My Report")

    def test_create_report_template_with_invalid_options(self):
        """Test creating a report template with invalid generator options"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["options"] = {"wrap_document": "invalid"}
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_report_template_with_invalid_status(self):
        """Test creating a report template with an invalid status"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["status"] = "invalid"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_report_template_with_invalid_default_format(self):
        """Test creating a report template with an unsupported default format"""
        data = self.generate_report_template_data(self.facilty.external_id)
        data["default_format"] = "docx"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_report_template_with_missing_fields(self):
        """Test creating a report template with missing required fields"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_url(), {"name": "Test"}, format="json")
        self.assertEqual(response.status_code, 400)

    # Test cases for retrieve report template

    def test_retrieve_report_template_as_superuser(self):
        """Test retrieving a facility report template as a superuser"""
        template = self.create_report_template(facility=self.facilty)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(template.slug))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(template.external_id))
        self.assertEqual(response.data["facility"]["id"], str(self.facilty.external_id))
        self.assertEqual(response.data["template_data"], template.template_data)

    def test_retrieve_report_template_as_user_with_permission(self):
        """Test retrieving a facility report template as a user with read permission"""
        template = self.create_report_template(facility=self.facilty)
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_read_template]
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.get_detail_url(template.slug))
        self.assertEqual(response.status_code, 200)

    def test_retrieve_report_template_as_regular_user(self):
        """Test retrieving a facility report template as a user without permission"""
        template = self.create_report_template(facility=self.facilty)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_detail_url(template.slug))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to read templates"
        )

    def test_retrieve_global_report_template_as_regular_user(self):
        """Test retrieving an instance level report template as a regular user"""
        template = self.create_report_template()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_detail_url(template.slug))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["slug_config"], {"slug_value": "test-report-template"}
        )
        self.assertIsNone(response.data["facility"])

    def test_retrieve_report_template_with_invalid_slug(self):
        """Test retrieving a report template that does not exist"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url("i-invalid-slug"))
        self.assertEqual(response.status_code, 404)

    # Test cases for update report template

    def test_update_report_template_as_superuser(self):
        """Test updating a facility report template as a superuser"""
        template = self.create_report_template(facility=self.facilty)
        data = self.generate_report_template_data(None)
        data["name"] = "Updated Report Template"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Report Template")
        self.assertEqual(response.data["slug"], template.slug)
        template.refresh_from_db()
        self.assertEqual(template.name, "Updated Report Template")
        self.assertEqual(template.updated_by, self.superuser)

    def test_update_report_template_as_user_with_permission(self):
        """Test updating a facility report template as a user with write permission"""
        template = self.create_report_template(facility=self.facilty)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_update_report_template_as_regular_user(self):
        """Test updating a facility report template as a user without permission"""
        template = self.create_report_template(facility=self.facilty)
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write templates"
        )

    def test_update_global_report_template_as_superuser(self):
        """Test updating an instance level report template as a superuser"""
        template = self.create_report_template()
        data = self.generate_report_template_data(None)
        data["name"] = "Updated Report Template"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], template.slug)

    def test_update_global_report_template_as_user_with_permission(self):
        """Test updating an instance level report template as a non superuser"""
        template = self.create_report_template()
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write templates"
        )

    def test_update_report_template_slug(self):
        """Test updating the slug of a facility report template"""
        template = self.create_report_template(facility=self.facilty)
        data = self.generate_report_template_data(None)
        data["slug_value"] = "updated-report-template"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["slug"],
            f"f-{self.facilty.external_id}-updated-report-template",
        )

    def test_update_report_template_with_duplicate_slug(self):
        """Test updating a facility report template to an existing slug"""
        template = self.create_report_template(facility=self.facilty)
        self.create_report_template(facility=self.facilty, slug="existing-template")
        data = self.generate_report_template_data(None)
        data["slug_value"] = "existing-template"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Slug already exists.", str(response.data))

    def test_update_global_report_template_with_duplicate_slug(self):
        """Test updating an instance level report template to an existing slug"""
        template = self.create_report_template()
        self.create_report_template(slug="existing-template")
        data = self.generate_report_template_data(None)
        data["slug_value"] = "existing-template"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Slug already exists.", str(response.data))

    def test_update_report_template_with_invalid_data(self):
        """Test updating a report template with an invalid template type"""
        template = self.create_report_template(facility=self.facilty)
        data = self.generate_report_template_data(None)
        data["template_type"] = "invalid_type"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_update_report_template_with_invalid_slug(self):
        """Test updating a report template that does not exist"""
        data = self.generate_report_template_data(None)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url("i-invalid-slug"), data, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_partial_update_report_template(self):
        """Test partially updating a report template"""
        template = self.create_report_template(facility=self.facilty)
        data = self.generate_report_template_data(None)
        data["name"] = "Patched Report Template"
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            self.get_detail_url(template.slug), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Patched Report Template")

    # Test cases for list report templates

    def test_list_report_templates_without_facility(self):
        """Test listing report templates without a facility returns instance templates"""
        global_template = self.create_report_template()
        self.create_report_template(facility=self.facilty)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(global_template.external_id)],
        )
        self.assertNotIn("template_data", response.data["results"][0])

    def test_list_report_templates_with_facility(self):
        """Test listing report templates of a facility"""
        self.create_report_template()
        facility_template = self.create_report_template(facility=self.facilty)
        other_facility = self.create_facility(user=self.superuser)
        self.create_report_template(facility=other_facility)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_url(), {"facility": self.facilty.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(facility_template.external_id)],
        )

    def test_list_report_templates_with_facility_only(self):
        """Test listing report templates of a facility with facility_only filter"""
        self.create_report_template()
        facility_template = self.create_report_template(facility=self.facilty)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_url(),
            {"facility": self.facilty.external_id, "facility_only": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(facility_template.external_id)],
        )

    def test_list_report_templates_as_user_with_permission(self):
        """Test listing facility report templates as a user with read permission"""
        self.create_report_template(facility=self.facilty)
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_read_template]
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(
            self.get_url(), {"facility": self.facilty.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_report_templates_as_regular_user(self):
        """Test listing facility report templates as a user without permission"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_url(), {"facility": self.facilty.external_id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to read templates"
        )

    def test_list_report_templates_with_invalid_facility(self):
        """Test listing report templates of a facility that does not exist"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_url(), {"facility": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 404)

    def test_list_report_templates_filter_by_name(self):
        """Test filtering report templates by name"""
        template = self.create_report_template(name="Discharge Template")
        self.create_report_template(slug="other-template", name="Other Template")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_url(), {"name": "discharge"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(template.external_id)],
        )

    def test_list_report_templates_filter_by_status(self):
        """Test filtering report templates by status"""
        template = self.create_report_template(status="draft")
        self.create_report_template(slug="other-template")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_url(), {"status": "draft"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(template.external_id)],
        )

    def test_list_report_templates_filter_by_template_type(self):
        """Test filtering report templates by template type"""
        template = self.create_report_template(
            template_type="patient_summary", context="patient_base"
        )
        self.create_report_template(slug="other-template")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_url(), {"template_type": "patient_summary"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(template.external_id)],
        )

    def test_list_report_templates_ordering_by_name(self):
        """Test ordering report templates by name"""
        self.create_report_template(name="B Template")
        self.create_report_template(slug="other-template", name="A Template")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_url(), {"ordering": "name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["name"] for item in response.data["results"]],
            ["A Template", "B Template"],
        )

    # Test cases for report template schema

    def test_get_schema_as_superuser(self):
        """Test fetching the template schema as a superuser"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_schema_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("encounter_base", str(response.data))

    def test_get_schema_as_user_with_permission(self):
        """Test fetching the template schema as a user with permission"""
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_view_template_schema]
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.get_schema_url())
        self.assertEqual(response.status_code, 200)

    def test_get_schema_as_regular_user(self):
        """Test fetching the template schema as a user without permission"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_schema_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to access template schema",
        )

    def test_get_schema_when_generation_fails(self):
        """Test fetching the template schema when schema generation fails"""
        self.client.force_authenticate(user=self.superuser)
        with (
            patch(
                "care.emr.api.viewsets.report.template.build_schema",
                side_effect=Exception("Schema error"),
            ),
            self.assertLogs(
                "care.emr.api.viewsets.report.template", level="ERROR"
            ) as schema_logs,
            self.assertLogs("django.request", level="ERROR") as request_logs,
        ):
            response = self.client.get(self.get_schema_url())
        self.assertEqual(
            schema_logs.records[0].getMessage(),
            "Failed to generate schema: Schema error",
        )
        self.assertEqual(
            request_logs.records[0].getMessage(),
            f"Internal Server Error: {self.get_schema_url()}",
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {"error": "Failed to generate schema"})

    # Test cases for report template preview

    def test_preview_report_template_as_superuser(self):
        """Test previewing a report template as a superuser"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.get_preview_url(), self.generate_preview_data(), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Discharge Summary", response.content.decode())

    def test_preview_report_template_as_user_with_permission(self):
        """Test previewing a report template as a user with permission"""
        user = self.create_user_with_permissions(
            [TemplatePermissions.can_preview_template]
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.get_preview_url(), self.generate_preview_data(), format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_preview_report_template_as_regular_user(self):
        """Test previewing a report template as a user without permission"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_preview_url(), self.generate_preview_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to preview templates"
        )

    def test_preview_report_template_with_options(self):
        """Test previewing a report template with generator options"""
        data = self.generate_preview_data(
            template_data="<p>Hello</p>",
            options={"wrap_document": True, "title": "Preview Title"},
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_preview_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Preview Title", response.content.decode())

    def test_preview_report_template_with_invalid_output_format(self):
        """Test previewing a report template with an unsupported output format"""
        data = self.generate_preview_data(output_format="docx")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_preview_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid output format", str(response.data))

    def test_preview_report_template_with_invalid_context(self):
        """Test previewing a report template with an unregistered context"""
        data = self.generate_preview_data(context="invalid_context")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_preview_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid context", str(response.data))

    def test_preview_report_template_with_missing_fields(self):
        """Test previewing a report template with missing required fields"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.get_preview_url(), {"output_format": "html"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_preview_report_template_with_invalid_options(self):
        """Test previewing a report template with invalid generator options"""
        data = self.generate_preview_data(options={"wrap_document": "invalid"})
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.get_preview_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Preview generation failed", str(response.data))

    def test_preview_report_template_with_invalid_template(self):
        """Test previewing a report template with invalid template syntax"""
        data = self.generate_preview_data(template_data="{% if %}")
        self.client.force_authenticate(user=self.superuser)
        with self.assertLogs(
            "care.emr.reports.renderer.renderer", level="ERROR"
        ) as renderer_logs:
            response = self.client.post(self.get_preview_url(), data, format="json")
        self.assertIn(
            "Template rendering failed: Template syntax error",
            renderer_logs.records[0].getMessage(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Preview generation failed", str(response.data))
