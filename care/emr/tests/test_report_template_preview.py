import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from care.emr.api.viewsets.report.template import TemplateViewSet
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.user import SingleUserIdContextBuilder
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.renderer.renderer import Renderer
from care.security.authorization.base import AuthorizationController
from care.users.models import User


@override_settings(DEBUG=False)
class ReportTemplatePreviewSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TemplateViewSet.as_view({"post": "preview"})
        self.user = User(
            id=1,
            username="report-author",
            first_name="Private",
            last_name="Requester",
            password="private-password-hash",
            totp_secret="private-totp-secret",
            is_superuser=False,
        )

    def preview(self, template_data, output_format="html", *, authenticated=True):
        request = self.factory.post(
            "/api/v1/template/preview/",
            {
                "template_data": template_data,
                "output_format": output_format,
                "context": "account_base",
            },
            format="json",
        )
        if authenticated:
            force_authenticate(request, user=self.user)
        response = self.view(request)
        if hasattr(response, "render"):
            response.render()
        return response

    def test_preview_uses_sample_identity_instead_of_request_user(self):
        with patch.object(AuthorizationController, "call", return_value=True) as auth:
            response = self.preview(
                "<p>{{ account.name }}: {{ current_user.full_name }}</p>"
            )

        auth.assert_called_once_with("can_preview_template", self.user)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "General Checkup Account")
        self.assertContains(response, "John Doe")
        self.assertNotContains(response, "Private Requester")
        self.assertNotContains(response, self.user.password)
        self.assertNotContains(response, self.user.totp_secret)

    def test_model_traversal_is_rejected_for_html_and_pdf(self):
        payloads = [
            "{{ current_user.context.password }}",
            "{{ current_user['context']['totp_secret'] }}",
            "{{ current_user.get_context().auth_token.key }}",
            (
                "{% for membership in current_user.context.facilityorganizationuser_set.all() %}"
                "{% for peer in membership.organization.facilityorganizationuser_set.all() %}"
                "{{ peer.user.password }}{{ peer.user.totp_secret }}{{ peer.user.auth_token.key }}"
                "{% endfor %}{% endfor %}"
            ),
        ]
        for output_format in ("html", "pdf"):
            for payload in payloads:
                with (
                    self.subTest(output_format=output_format, payload=payload),
                    patch.object(AuthorizationController, "call", return_value=True),
                ):
                    response = self.preview(payload, output_format)
                    self.assertEqual(response.status_code, 400)
                    self.assertNotContains(
                        response, self.user.password, status_code=400
                    )
                    self.assertNotContains(
                        response, self.user.totp_secret, status_code=400
                    )

    def test_html_preview_removes_external_resource_and_navigation_urls(self):
        url = "https://report-exfil.example/collect"
        template = (
            f'<meta http-equiv="refresh" content="0;url={url}">'
            f'<link rel="stylesheet" href="{url}">'
            f'<style>@import url("{url}");</style>'
            f'<img src="{url}"><p>Report</p>'
        )
        with patch.object(AuthorizationController, "call", return_value=True):
            response = self.preview(template)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report")
        self.assertNotContains(response, url)
        self.assertIn("Content-Security-Policy", response)

    def test_pdf_preview_never_opens_external_or_local_resources(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "report-secret.txt"
            secret_file.write_text("private report worker secret")
            template = (
                '<img src="http://127.0.0.1:6379/probe">'
                f'<link rel="attachment" href="{secret_file.as_uri()}">'
                "<p>Report</p>"
            )
            with (
                patch.object(AuthorizationController, "call", return_value=True),
                patch("urllib.request.OpenerDirector.open", autospec=True) as open_url,
            ):
                response = self.preview(template, "pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        open_url.assert_not_called()

    def test_preview_requires_permission(self):
        with patch.object(AuthorizationController, "call", return_value=False) as auth:
            response = self.preview("<p>Report</p>")

        auth.assert_called_once_with("can_preview_template", self.user)
        self.assertEqual(response.status_code, 403)

    def test_preview_requires_authentication(self):
        with patch.object(AuthorizationController, "call") as auth:
            response = self.preview("<p>Report</p>", authenticated=False)

        self.assertEqual(response.status_code, 403)
        auth.assert_not_called()

    def test_bundled_reports_still_render_without_external_resource_access(self):
        templates = json.loads(
            (settings.BASE_DIR / "data/template_fixtures.json").read_text()
        )
        for template in templates:
            context_class = DataPointRegistry.get(template["context"])
            context = {
                context_class.context_key: context_class(is_preview=True),
                "current_user": SingleUserIdContextBuilder(is_preview=True),
            }
            for output_format in ("html", "pdf"):
                with self.subTest(
                    template=template["name"], output_format=output_format
                ):
                    generator = GeneratorRegistry.get(output_format)()
                    options = generator.options_model.model_validate(
                        template.get("options", {})
                    )
                    with patch(
                        "urllib.request.OpenerDirector.open", autospec=True
                    ) as open_url:
                        content = Renderer(generator).render(
                            template["template_data"], context, options
                        )
                    open_url.assert_not_called()
                    self.assertTrue(content)
                    if output_format == "pdf":
                        self.assertTrue(content.startswith(b"%PDF-"))
                    else:
                        self.assertIn(b"Treatment Summary", content)
