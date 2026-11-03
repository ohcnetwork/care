from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.request import OpenerDirector

from django.test import SimpleTestCase
from weasyprint.urls import URLFetcher

from care.emr.reports.renderer.generators.weasyprint_generator import (
    WeasyPrintGenerator,
    WeasyPrintGeneratorOptions,
)


class ReportPDFResourceSecurityTests(SimpleTestCase):
    def setUp(self):
        self.generator = WeasyPrintGenerator()

    def test_external_resources_never_reach_network_or_filesystem(self):
        urls = {
            "image": "http://127.0.0.1:6379/image.png",
            "stylesheet": "https://example.com/report.css",
            "import": "http://169.254.169.254/import.css",
            "background": "ftp://example.com/background.png",
            "font": "file:///etc/report-font.ttf",
            "svg_image": "http://localhost/svg-image.png",
        }
        svg = (
            "data:image/svg+xml,"
            '%3Csvg xmlns="http://www.w3.org/2000/svg" width="20" height="20"%3E'
            f'%3Cimage href="{urls["svg_image"]}" width="20" height="20"/%3E'
            "%3C/svg%3E"
        )
        html = f"""
            <link rel="stylesheet" href="{urls["stylesheet"]}">
            <style>
                @import url("{urls["import"]}");
                @font-face {{ font-family: ReportFont; src: url("{urls["font"]}"); }}
                p {{ font-family: ReportFont; background: url("{urls["background"]}"); }}
            </style>
            <p>Report</p>
            <img src="{urls["image"]}">
            <img src='{svg}'>
        """
        fetch = URLFetcher.fetch
        open_resource = OpenerDirector.open

        def open_embedded_resource(fetcher, request, *args, **kwargs):
            if request.type != "data":
                raise ValueError("External resource reached the transport")
            return open_resource(fetcher, request, *args, **kwargs)

        with (
            patch.object(
                URLFetcher, "fetch", autospec=True, side_effect=fetch
            ) as fetch_url,
            patch(
                "urllib.request.OpenerDirector.open",
                autospec=True,
                side_effect=open_embedded_resource,
            ) as open_url,
        ):
            pdf = self.generator.generate(html)

        requested_urls = {call.args[1] for call in fetch_url.call_args_list}
        self.assertTrue(set(urls.values()).issubset(requested_urls), requested_urls)
        open_url.assert_called_once()  # Only the inline SVG is opened.
        self.assertTrue(open_url.call_args.args[1].full_url.startswith("data:"))
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_local_file_cannot_be_embedded_as_a_pdf_attachment(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "report-secret.txt"
            secret_file.write_text("private report worker secret")
            html = (
                f'<link rel="attachment" href="{secret_file.as_uri()}">'
                f'<a rel="attachment" href="{secret_file.as_uri()}">Download</a>'
                "<p>Report</p>"
            )
            with patch("urllib.request.OpenerDirector.open", autospec=True) as open_url:
                pdf = self.generator.generate(html)

        open_url.assert_not_called()
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertNotIn(b"/EmbeddedFiles", pdf)
        self.assertNotIn(b"/Type /EmbeddedFile", pdf)

    def test_option_stylesheets_cannot_load_external_resources(self):
        options = WeasyPrintGeneratorOptions(
            stylesheets=[
                '@import url("https://example.com/report.css");'
                'p { background-image: url("file:///etc/background.png"); }'
            ]
        )
        with patch("urllib.request.OpenerDirector.open", autospec=True) as open_url:
            pdf = self.generator.generate("<p>Report</p>", options)

        open_url.assert_not_called()
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_inline_data_images_and_stylesheets_still_render(self):
        image = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
        )
        html = (
            '<link rel="stylesheet" href="data:text/css,p%20%7Bcolor:red%7D">'
            f'<p>Report</p><img src="{image}">'
        )
        pdf = self.generator.generate(html)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIn(b"/Subtype /Image", pdf)
