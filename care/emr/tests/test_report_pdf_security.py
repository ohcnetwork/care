from base64 import b64decode
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, OpenerDirector

from django.test import SimpleTestCase, override_settings
from PIL import UnidentifiedImageError
from weasyprint.document import Document
from weasyprint.images import SVGImage
from weasyprint.urls import URLFetcher, URLFetcherResponse

from care.emr.reports.renderer.generators.weasyprint_generator import (
    ReportURLFetcher,
    WeasyPrintGenerator,
    WeasyPrintGeneratorOptions,
)
from care.emr.reports.renderer.resource_policy import FONT_MIME_TYPES

IMAGE_ORIGIN = "https://assets.example"
REMOTE_IMAGE = f"{IMAGE_ORIGIN}/logo.png"
IMAGE_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGNkYPjPwMDAxAAGAAsfAQMU4wsAAAAAAElFTkSuQmCC"
)
# A generated TrueType font containing only a space and a triangular "A" glyph.
FONT_BYTES = b64decode(
    "AAEAAAAKAIAAAwAgT1MvMkUARDUAAAEoAAAAYGNtYXAAdABcAAABkAAAADxnbHlmGN77eQAAAdQA"
    "AAAYaGVhZC+PvJYAAACsAAAANmhoZWEEsgJaAAAA5AAAACRobXR4AlgAAAAAAYgAAAAIbG9jYQAA"
    "AAwAAAHMAAAACG1heHAABQAFAAABCAAAACBuYW1lEUXUPgAAAewAAAC9cG9zdAAIACQAAAKsAAAA"
    "KAABAAAAAQAAWRj1Hl8PPPUAAQPoAAAAAOcRvH0AAAAA5xG8fQBkAAAB9AK8AAAAAwACAAAAAAAA"
    "AAEAAAMg/zgAAAJYAAAAyAGQAAEAAAAAAAAAAAAAAAAAAAABAAEAAAADAAMAAQAAAAAAAgAAAAAAAAAA"
    "AAAAAAAAAAAAAwJYAZAABQAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAA"
    "AAAAAAAAPz8/PwAAACAAQQMg/zgAAAMgAMgAAAAAAAAAAAAAAAAAAAAgAAACWAAAAAAAAAAAAAIAAAAD"
    "AAAAFAADAAEAAAAUAAQAKAAAAAYABAABAAIAIABB//8AAAAgAEH////h/8EAAQAAAAAAAAAAAAAAAAAM"
    "AAEAZAAAAfQCvAACAAAzExNkyMgCvP1EAAAACgB+AAEAAAAAAAEADgAAAAEAAAAAAAIABwAOAAEAAAAA"
    "AAMADgAAAAEAAAAAAAQADgAAAAEAAAAAAAYADgAAAAMAAQQJAAEAHAAVAAMAAQQJAAIADgAxAAMAAQQJ"
    "AAMAHAAVAAMAAQQJAAQAHAAVAAMAAQQJAAYAHAAVUmVwb3J0VGVzdEZvbnRSZWd1bGFyAFIAZQBw"
    "AG8AcgB0AFQAZQBzAHQARgBvAG4AdABSAGUAZwB1AGwAYQByAAAAAAIAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAwAAAAMAJA=="
)


class ReportPDFResourceSecurityTests(SimpleTestCase):
    def setUp(self):
        self.generator = WeasyPrintGenerator()

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_configured_remote_image_is_embedded_in_pdf(self):
        response = URLFetcherResponse(
            REMOTE_IMAGE, IMAGE_BYTES, {"Content-Type": "image/png"}
        )
        with patch(
            "urllib.request.OpenerDirector.open", autospec=True, return_value=response
        ) as open_url:
            pdf = self.generator.generate(f'<p>Report</p><img src="{REMOTE_IMAGE}">')

        open_url.assert_called_once()
        self.assertEqual(open_url.call_args.args[1].full_url, REMOTE_IMAGE)
        self.assertIn(b"/Subtype /Image", pdf)

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_trusted_stylesheets_imports_and_relative_fonts_render_in_pdf(self):
        stylesheet_url = f"{IMAGE_ORIGIN}/css/report.css"
        imported_url = f"{IMAGE_ORIGIN}/css/nested/layout.css"
        font_url = f"{IMAGE_ORIGIN}/fonts/report.ttf"
        resources = {
            stylesheet_url: ("text/css", '@import "nested/layout.css";'),
            imported_url: (
                "text/css",
                '@import "https://untrusted.example/report.css";'
                "@font-face {font-family: ReportTestFont;"
                'src: url("../../fonts/report.ttf") format("truetype");}'
                "@font-face {font-family: UntrustedFont;"
                'src: url("https://untrusted.example/font.ttf");}'
                "p {font-family: ReportTestFont;"
                'background-image: url("https://untrusted.example/image.png");}',
            ),
            font_url: ("font/ttf", FONT_BYTES),
        }
        write_pdf = Document.write_pdf
        rendered_families = []

        def open_resource(fetcher, request, *args, **kwargs):
            content_type, body = resources[request.full_url]
            return URLFetcherResponse(
                request.full_url, body, {"Content-Type": content_type}
            )

        def record_font_families(document, *args, **kwargs):
            pdf = write_pdf(document, *args, **kwargs)
            rendered_families.extend(font.family for font in document.fonts.values())
            return pdf

        for source in ("link", "options"):
            with (
                self.subTest(source=source),
                patch(
                    "urllib.request.OpenerDirector.open",
                    autospec=True,
                    side_effect=open_resource,
                ) as open_url,
                patch.object(
                    Document,
                    "write_pdf",
                    autospec=True,
                    side_effect=record_font_families,
                ),
            ):
                rendered_families.clear()
                html = "<p>A</p>"
                options = None
                if source == "link":
                    html = f'<link rel="stylesheet" href="{stylesheet_url}">' + html
                else:
                    options = WeasyPrintGeneratorOptions(
                        stylesheets=[f'@import url("{stylesheet_url}");']
                    )
                pdf = self.generator.generate(html, options)

                self.assertEqual(
                    {call.args[1].full_url for call in open_url.call_args_list},
                    set(resources),
                )
                self.assertIn("ReportTestFont", rendered_families)
                self.assertTrue(pdf.startswith(b"%PDF-"))

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_configured_resource_origin_cannot_serve_active_content(self):
        for content_type in (
            "text/html",
            "image/svg+xml",
            "application/javascript",
            "application/pdf",
        ):
            with self.subTest(content_type=content_type):
                response = URLFetcherResponse(
                    REMOTE_IMAGE, b"remote resource", {"Content-Type": content_type}
                )
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    patch.object(response, "close", wraps=response.close) as close,
                ):
                    with self.assertRaisesMessage(
                        ValueError, "must be images, CSS, or fonts"
                    ):
                        ReportURLFetcher().fetch(REMOTE_IMAGE)
                    close.assert_called_once()

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_configured_image_fetcher_does_not_follow_redirects(self):
        fetcher = ReportURLFetcher()
        self.assertFalse(
            any(
                isinstance(handler, HTTPRedirectHandler) for handler in fetcher.handlers
            )
        )
        error = HTTPError(
            REMOTE_IMAGE, 302, "Found", {"Location": "http://127.0.0.1/private"}, None
        )
        with patch(
            "urllib.request.OpenerDirector.open", autospec=True, side_effect=error
        ) as open_url:
            pdf = self.generator.generate(f'<img src="{REMOTE_IMAGE}">')
        open_url.assert_called_once()
        self.assertNotIn(b"/Subtype /Image", pdf)

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_svg_cannot_bypass_remote_image_check_with_a_raster_content_type(self):
        response = URLFetcherResponse(
            REMOTE_IMAGE,
            b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"></svg>',
            {"Content-Type": "image/png"},
        )
        with (
            patch(
                "urllib.request.OpenerDirector.open",
                autospec=True,
                return_value=response,
            ) as open_url,
            patch.object(response, "close", wraps=response.close) as close,
        ):
            with self.assertRaises(UnidentifiedImageError):
                ReportURLFetcher().fetch(REMOTE_IMAGE)
            close.assert_called_once()
        open_url.assert_called_once()

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_xml_cannot_bypass_remote_image_check_with_css_or_font_content_types(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            '<rect width="20" height="20" fill="red"/></svg>'
        )
        payloads = (
            svg.encode(),
            ('<?xml version="1.0" encoding="UTF-8"?>' + svg).encode(),
            b"\xef\xbb\xbf" + svg.encode(),
            svg.encode("utf-16"),
            ("<!-- SVG asset -->" + svg).encode(),
            ('<!DOCTYPE svg [<!ENTITY label "Report">]>' + svg).encode(),
            svg.replace("<svg", "<s:svg")
            .replace("</svg>", "</s:svg>")
            .replace("xmlns=", "xmlns:s=")
            .encode(),
            f'<report width="20" height="20">{svg}</report>'.encode(),
        )
        for content_type in sorted(FONT_MIME_TYPES | {"text/css"}):
            for payload in payloads:
                with self.subTest(content_type=content_type, payload=payload):
                    response = URLFetcherResponse(
                        REMOTE_IMAGE, payload, {"Content-Type": content_type}
                    )
                    with (
                        patch(
                            "urllib.request.OpenerDirector.open",
                            autospec=True,
                            return_value=response,
                        ) as open_url,
                        patch.object(response, "close", wraps=response.close) as close,
                    ):
                        with self.assertRaises(ValueError):
                            ReportURLFetcher().fetch(REMOTE_IMAGE)
                        close.assert_called_once()
                    open_url.assert_called_once()

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_mislabeled_remote_svg_never_reaches_weasyprint_svg_renderer(self):
        svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            b'<rect width="20" height="20" fill="red"/></svg>'
        )
        for content_type in ("text/css", "font/woff2"):
            with self.subTest(content_type=content_type):
                response = URLFetcherResponse(
                    REMOTE_IMAGE, svg, {"Content-Type": content_type}
                )
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ) as open_url,
                    patch("weasyprint.images.SVGImage", wraps=SVGImage) as render_svg,
                    patch.object(response, "close", wraps=response.close) as close,
                ):
                    pdf = self.generator.generate(f'<img src="{REMOTE_IMAGE}">')
                self.assertTrue(pdf.startswith(b"%PDF-"))
                render_svg.assert_not_called()
                close.assert_called_once()
                open_url.assert_called_once()

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_trusting_image_origin_does_not_open_other_origins_or_local_files(self):
        for url in (
            "https://untrusted.example/logo.png",
            "http://127.0.0.1/logo.png",
            "https://169.254.169.254/logo.png",
            "file:///etc/passwd",
            IMAGE_ORIGIN + ".evil.example/logo.png",
            IMAGE_ORIGIN + ":444/logo.png",
            IMAGE_ORIGIN + "@evil.example/logo.png",
        ):
            with (
                self.subTest(url=url),
                patch("urllib.request.OpenerDirector.open", autospec=True) as open_url,
            ):
                with self.assertRaisesMessage(ValueError, "origin is not allowed"):
                    ReportURLFetcher().fetch(url)
                open_url.assert_not_called()

    def test_external_resources_never_reach_network_or_filesystem(self):
        urls = {
            "image": "http://127.0.0.1:6379/image.png",
            "stylesheet": "https://untrusted.example/report.css",
            "import": "http://169.254.169.254/import.css",
            "background": "ftp://untrusted.example/background.png",
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
        self.assertEqual(len(requested_urls), 1)  # Only data reaches the base fetcher.
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
                '@import url("https://untrusted.example/report.css");'
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
