import logging
import zlib
from gzip import GzipFile
from io import BytesIO
from typing import Any, Literal
from urllib.request import OpenerDirector, Request
from xml.parsers import expat

from django.conf import settings
from django.http import HttpResponse
from PIL import Image
from pydantic import Field
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import URLFetcher, URLFetcherResponse, iri_to_uri

from care.emr.reports.renderer.generators.base import BaseOptions, BaseOutputGenerator
from care.emr.reports.renderer.resource_policy import (
    FONT_MIME_TYPES,
    IMAGE_MIME_TYPES,
    is_allowed_remote_resource,
)

logger = logging.getLogger(__name__)


class ReportURLFetcher(URLFetcher):
    _READ_CHUNK_SIZE = 64 * 1024

    def __init__(self):
        super().__init__(allowed_protocols={"data", "https"}, allow_redirects=False)

    @staticmethod
    def _reject_remote_xml(*_args):
        raise ValueError("Remote XML/SVG report resources are not allowed")

    @classmethod
    def _read_limited(cls, stream, limit):
        body = bytearray()
        while chunk := stream.read(min(cls._READ_CHUNK_SIZE, limit - len(body) + 1)):
            body.extend(chunk)
            if len(body) > limit:
                raise ValueError("Report resource exceeds maximum size")
        return bytes(body)

    @classmethod
    def _read_body(cls, response, limit):
        encodings = response.headers.get_all("Content-Encoding", [])
        encoding = encodings[0].strip().lower() if encodings else "identity"
        if len(encodings) > 1 or encoding not in {"identity", "gzip", "deflate"}:
            raise ValueError("Unsupported report resource content encoding")
        if encoding == "identity":
            return cls._read_limited(response, limit)

        # Bound compressed input too, allowing 64 KiB for compression framing.
        encoded = cls._read_limited(response, limit + cls._READ_CHUNK_SIZE)
        if encoding == "gzip":
            with GzipFile(fileobj=BytesIO(encoded)) as stream:
                return cls._read_limited(stream, limit)

        try:
            decoder = zlib.decompressobj()
            body = decoder.decompress(encoded, limit + 1)
        except zlib.error:
            # Some servers send raw DEFLATE without the zlib wrapper.
            decoder = zlib.decompressobj(-zlib.MAX_WBITS)
            body = decoder.decompress(encoded, limit + 1)
        if len(body) > limit:
            raise ValueError("Report resource exceeds maximum size")
        if not decoder.eof or decoder.unused_data:
            raise ValueError("Invalid or incomplete deflate report resource")
        return body

    @classmethod
    def _validate_body(cls, body, content_type):
        if content_type in IMAGE_MIME_TYPES:
            with Image.open(BytesIO(body)) as image:
                if Image.MIME.get(image.format) not in IMAGE_MIME_TYPES:
                    raise ValueError("Remote report resources must be raster images")
                image.verify()
        else:
            # WeasyPrint tries SVG for any non-raster image, regardless of MIME
            # type. Stop XML at its first element/doctype without building a tree.
            parser = expat.ParserCreate()
            parser.StartElementHandler = cls._reject_remote_xml
            parser.StartDoctypeDeclHandler = cls._reject_remote_xml
            try:
                parser.Parse(body, True)  # noqa: FBT003 - isfinal is positional-only.
            except expat.ExpatError:
                pass  # Ordinary CSS and font bytes are not XML documents.

    def fetch(self, url, headers=None):
        pending_request = self._request
        self._request = None
        embedded = url.lower().startswith("data:")
        if not embedded and not is_allowed_remote_resource(url):
            raise ValueError("Report resource origin is not allowed")
        if embedded:
            return super().fetch(url, headers)

        limit = settings.REPORT_MAX_RESOURCE_SIZE_BYTES
        if limit <= 0:
            raise ValueError("REPORT_MAX_RESOURCE_SIZE_BYTES must be positive")
        if pending_request is not None and pending_request.full_url == url:
            request = pending_request
        else:
            request = Request(  # noqa: S310 - Exact HTTPS origin checked above.
                iri_to_uri(url), headers={**self._http_headers, **(headers or {})}
            )
        # URLFetcher.fetch eagerly inflates deflate bodies. Open the transport
        # directly so both encoded and decoded reads are bounded here instead.
        response = OpenerDirector.open(self, request, timeout=self._timeout)
        try:
            content_type = response.headers.get_content_type()
            if content_type not in IMAGE_MIME_TYPES | FONT_MIME_TYPES | {"text/css"}:
                raise ValueError(
                    "Remote report resources must be images, CSS, or fonts"
                )
            body = self._read_body(response, limit)
            self._validate_body(body, content_type)
        finally:
            response.close()
        for header in ("Content-Encoding", "Content-Length"):
            if header in response.headers:
                del response.headers[header]
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
