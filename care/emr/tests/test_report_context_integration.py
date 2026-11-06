from jinja2.exceptions import SecurityError, UndefinedError
from rest_framework.authtoken.models import Token

from care.emr.reports.context_builder.data_points.encounter import (
    EncounterReportContext,
)
from care.emr.reports.context_builder.data_points.user import SingleUserIdContextBuilder
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.utils.tests.base import CareAPITestBase


class ReportContextIntegrationTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(first_name="Template", last_name="Author")
        self.facility = self.create_facility(user=self.user, name="Report Facility")
        self.organization = self.create_facility_organization(
            facility=self.facility, name="Clinical Department"
        )
        self.patient = self.create_patient(name="Report Patient")
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            care_team=[
                {
                    "user_id": self.user.id,
                    "role": {"display": "Primary clinician"},
                }
            ],
        )
        self.engine = TemplateEngine()
        self.context = {
            "current_user": SingleUserIdContextBuilder(context=self.user),
            "encounter": EncounterReportContext(context=self.encounter),
        }

    def test_nested_fields_and_queryset_filters_render_real_clinical_data(self):
        report = self.engine.render(
            "{{ encounter.patient.name }}|{{ encounter.facility.name }}|"
            "{% for membership in encounter.organizations.filter(limit=1) %}"
            "{{ membership.organization }};{% endfor %}|"
            "{% for member in encounter.care_team %}"
            "{{ member.user.full_name }}:{{ member.role }};{% endfor %}",
            self.context,
        )
        self.assertEqual(
            report,
            "Report Patient|Report Facility|Clinical Department;|"
            "Template Author:Primary clinician;",
        )

    def test_peer_credentials_and_service_tokens_are_unreachable_without_queries(self):
        role = self.create_role()
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        service_account = self.create_user(
            is_service_account=True,
            password="peer-password-hash",
            totp_secret="peer-totp-secret",
        )
        self.attach_role_facility_organization_user(
            self.organization, service_account, role
        )
        Token.objects.create(user=service_account)
        source = (
            "{% for membership in current_user.context.facilityorganizationuser_set.all() %}"
            "{% for peer in membership.organization.facilityorganizationuser_set.all() %}"
            "{{ peer.user.password }}{{ peer.user.totp_secret }}{{ peer.user.auth_token.key }}"
            "{% endfor %}{% endfor %}"
        )
        with (
            self.assertNumQueries(0),
            self.assertRaises((SecurityError, UndefinedError)),
        ):
            self.engine.render(source, self.context)

    def test_template_cannot_write_real_organization_or_encounter_caches(self):
        modified_date = self.organization.modified_date
        cached_organizations = self.encounter.facility_organization_cache.copy()
        for source in (
            "{{ encounter.context.sync_organization_cache() }}",
            "{% for membership in encounter.organizations %}"
            "{{ membership.context.organization.set_organization_cache() }}"
            "{% endfor %}",
        ):
            with (
                self.subTest(source=source),
                self.assertRaises((SecurityError, UndefinedError)),
            ):
                self.engine.render(source, self.context)

        self.organization.refresh_from_db()
        self.encounter.refresh_from_db()
        self.assertEqual(self.organization.modified_date, modified_date)
        self.assertEqual(
            self.encounter.facility_organization_cache, cached_organizations
        )
