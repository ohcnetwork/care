from html import escape
from typing import Any

from django.http import HttpResponse
from pydantic import Field

from care.emr.reports.renderer.generators.base import BaseOptions, BaseOutputGenerator
from care.emr.reports.renderer.generators.registry import GeneratorRegistry
from care.emr.reports.renderer.html_sanitizer import (
    REPORT_CONTENT_SECURITY_POLICY,
    sanitize_report_html,
)


class HTMLGeneratorOptions(BaseOptions):
    wrap_document: bool = Field(default=False)
    title: str = Field(default="Report")
    charset: str = Field(default="utf-8")


class HTMLGenerator(BaseOutputGenerator):
    options_model = HTMLGeneratorOptions

    def generate(self, html: str, options: HTMLGeneratorOptions | None = None) -> bytes:
        options = options or HTMLGeneratorOptions()
        if options.wrap_document and "<html" not in html.lower():
            html = self._wrap_html_document(html, options)
        return sanitize_report_html(html).encode("utf-8")

    def _wrap_html_document(
        self, html_fragment: str, options: HTMLGeneratorOptions
    ) -> str:
        title = escape(options.title)
        charset = escape(options.charset, quote=True)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="{charset}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 2em;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        table, th, td {{
            border: 1px solid #ddd;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
</head>
<body>
{html_fragment}
</body>
</html>"""

    def get_format(self) -> str:
        return "html"

    def get_supported_options(self) -> dict[str, Any]:
        return HTMLGeneratorOptions().model_dump()

    def get_http_response(self, content):
        response = HttpResponse(content, content_type="text/html; charset=utf-8")
        response["Content-Security-Policy"] = REPORT_CONTENT_SECURITY_POLICY
        response["X-Content-Type-Options"] = "nosniff"
        return response


GeneratorRegistry.register(
    format_type="html",
    generator_class=HTMLGenerator,
    mime_type="text/html",
    file_extension=".html",
)
