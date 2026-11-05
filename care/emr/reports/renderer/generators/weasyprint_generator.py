import logging
from io import BytesIO
from typing import Any, Literal
from xml.parsers import expat

from django.http import HttpResponse
from PIL import Image
from pydantic import Field
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetcher, URLFetcherResponse

from care.emr.reports.renderer.generators.base import BaseOptions, BaseOutputGenerator
from care.emr.reports.renderer.resource_policy import (
    FONT_MIME_TYPES,
    IMAGE_MIME_TYPES,
    is_allowed_remote_resource,
)

logger = logging.getLogger(__name__)


class ReportURLFetcher(URLFetcher):
    def __init__(self):
        super().__init__(allowed_protocols={"data", "https"}, allow_redirects=False)

    @staticmethod
    def _reject_remote_xml(*_args):
        raise ValueError("Remote XML/SVG report resources are not allowed")

    def fetch(self, url, headers=None):
        embedded = url.lower().startswith("data:")
        if not embedded and not is_allowed_remote_resource(url):
            raise ValueError("Report resource origin is not allowed")
        response = super().fetch(url, headers)
        if embedded:
            return response
        try:
            if response.content_type not in IMAGE_MIME_TYPES | FONT_MIME_TYPES | {
                "text/css"
            }:
                raise ValueError(
                    "Remote report resources must be images, CSS, or fonts"
                )
            body = response.read()
            if response.content_type in IMAGE_MIME_TYPES:
                with Image.open(BytesIO(body)) as image:
                    if Image.MIME.get(image.format) not in IMAGE_MIME_TYPES:
                        raise ValueError(
                            "Remote report resources must be raster images"
                        )
                    image.verify()
            else:
                # WeasyPrint tries SVG for any non-raster image, regardless of
                # MIME type. Reject XML before returning CSS/font bytes, stopping
                # at the first element or doctype without building an XML tree.
                parser = expat.ParserCreate()
                parser.StartElementHandler = self._reject_remote_xml
                parser.StartDoctypeDeclHandler = self._reject_remote_xml
                try:
                    parser.Parse(body, True)  # noqa: FBT003 - isfinal is positional-only.
                except expat.ExpatError:
                    pass  # Ordinary CSS and font bytes are not XML documents.
        finally:
            response.close()
        return URLFetcherResponse(response.url, body, response.headers, response.status)


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
            # Templates can load embedded assets, images, CSS, and fonts from explicitly
            # trusted origins. Files and redirects remain inaccessible.
            url_fetcher = ReportURLFetcher()
            font_config = FontConfiguration()
            html_obj = self.HTML(string=html, url_fetcher=url_fetcher)
            stylesheets = []

            if options.stylesheets:
                for css_string in options.stylesheets:
                    stylesheets.append(
                        self.CSS(
                            string=css_string,
                            url_fetcher=url_fetcher,
                            font_config=font_config,
                        )
                    )
            else:
                stylesheets.append(
                    self.CSS(
                        string=self._get_default_css(options),
                        url_fetcher=url_fetcher,
                        font_config=font_config,
                    )
                )

            return html_obj.write_pdf(stylesheets=stylesheets, font_config=font_config)
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
