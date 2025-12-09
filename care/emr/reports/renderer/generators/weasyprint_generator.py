import logging
from typing import Any, Literal

from django.http import HttpResponse
from pydantic import Field
from weasyprint import CSS, HTML

from care.emr.reports.renderer.generators.base import BaseOptions, BaseOutputGenerator

logger = logging.getLogger(__name__)


class WeasyPrintGeneratorOptions(BaseOptions):
    page_size: Literal["A4", "A3", "A5", "Letter", "Legal"] = Field(default="A4")
    margin: str = Field(default="1cm")
    orientation: Literal["portrait", "landscape"] = Field(default="portrait")
    stylesheets: list[str] = Field(default=[])


class WeasyPrintGenerator(BaseOutputGenerator):
    options_model = WeasyPrintGeneratorOptions

    def __init__(self):
        self.HTML = HTML
        self.CSS = CSS

    def generate(
        self, html: str, options: WeasyPrintGeneratorOptions | None = None
    ) -> bytes:
        options = options or WeasyPrintGeneratorOptions()
        try:
            html_obj = self.HTML(string=html)
            stylesheets = []

            if options.stylesheets:
                for css_string in options.stylesheets:
                    stylesheets.append(self.CSS(string=css_string))
            else:
                stylesheets.append(self.CSS(string=self._get_default_css(options)))

            return html_obj.write_pdf(stylesheets=stylesheets)
        except Exception as e:
            logger.error("WeasyPrint PDF generation failed: %s", e)
            msg = f"Failed to generate PDF: {e!s}"
            raise Exception(msg) from e

    def _get_default_css(self, options: WeasyPrintGeneratorOptions) -> str:
        page_size = options.page_size
        margin = options.margin
        orientation = options.orientation

        return f"""
        @page {{
            size: {page_size} {orientation};
            margin: {margin};
        }}
        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
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
            font-weight: bold;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 0.5em;
            margin-bottom: 0.5em;
            page-break-after: avoid;
        }}
        p {{
            margin: 0.5em 0;
        }}
        ul, ol {{
            margin: 0.5em 0;
            padding-left: 2em;
        }}
        """

    def get_format(self) -> str:
        return "pdf"

    def get_supported_options(self) -> dict[str, Any]:
        return WeasyPrintGeneratorOptions().model_dump()

    def get_http_response(self, content):
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="template_preview.pdf"'
        return response


def _register():
    from care.emr.reports.renderer.generators.registry import GeneratorRegistry

    GeneratorRegistry.register("pdf", WeasyPrintGenerator, "application/pdf", ".pdf")


_register()
