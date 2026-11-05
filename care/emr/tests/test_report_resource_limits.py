import gzip
import zlib
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from weasyprint.urls import URLFetcherResponse

from care.emr.reports.renderer.generators.weasyprint_generator import ReportURLFetcher
from care.emr.tests.test_report_pdf_security import FONT_BYTES, IMAGE_BYTES

ASSET_ORIGIN = "https://assets.example"
ASSET_URL = f"{ASSET_ORIGIN}/resource"
BODY_LIMIT = 1024


class BoundedReadStream(BytesIO):
    """Fail if the fetcher tries to buffer an unbounded transport response."""

    def __init__(self, body):
        super().__init__(body)
        self.bytes_read = 0
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        if size < 0:
            raise AssertionError("Transport reads must specify a bounded size")
        result = super().read(size)
        self.bytes_read += len(result)
        return result


def encoded_response(body, encoding):
    if encoding == "gzip":
        return gzip.compress(body), {"Content-Encoding": "gzip"}
    if encoding == "deflate":
        return zlib.compress(body), {"Content-Encoding": "deflate"}
    if encoding == "raw-deflate":
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        return compressor.compress(body) + compressor.flush(), {
            "Content-Encoding": "deflate"
        }
    return body, {}


@override_settings(
    REPORT_ALLOWED_RESOURCE_ORIGINS=[ASSET_ORIGIN],
    REPORT_MAX_RESOURCE_SIZE_BYTES=BODY_LIMIT,
)
class ReportResourceLimitsTests(SimpleTestCase):
    def test_oversized_resources_are_rejected_before_validation(self):
        body = b"a" * (BODY_LIMIT + 1)
        for content_type in ("image/png", "text/css", "font/woff2"):
            for encoding in (None, "gzip", "deflate", "raw-deflate"):
                with self.subTest(content_type=content_type, encoding=encoding):
                    encoded, headers = encoded_response(body, encoding)
                    stream = BoundedReadStream(encoded)
                    response = URLFetcherResponse(
                        ASSET_URL, stream, {"Content-Type": content_type, **headers}
                    )
                    with (
                        patch(
                            "urllib.request.OpenerDirector.open",
                            autospec=True,
                            return_value=response,
                        ),
                        patch(
                            "care.emr.reports.renderer.generators.weasyprint_generator.Image.open"
                        ) as validate_image,
                    ):
                        with self.assertRaisesMessage(ValueError, "maximum size"):
                            ReportURLFetcher().fetch(ASSET_URL)
                        validate_image.assert_not_called()
                    self.assertTrue(stream.closed)

    def test_exact_limit_images_css_and_fonts_preserve_decoded_bytes(self):
        resources = (
            ("image/png", IMAGE_BYTES),
            ("text/css", b"p { color: red; }"),
            ("font/ttf", FONT_BYTES),
        )
        for content_type, body in resources:
            for encoding in (None, "gzip", "deflate", "raw-deflate"):
                with (
                    self.subTest(content_type=content_type, encoding=encoding),
                    override_settings(REPORT_MAX_RESOURCE_SIZE_BYTES=len(body)),
                ):
                    encoded, headers = encoded_response(body, encoding)
                    stream = BoundedReadStream(encoded)
                    response = URLFetcherResponse(
                        ASSET_URL, stream, {"Content-Type": content_type, **headers}
                    )
                    with patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ):
                        fetched = ReportURLFetcher().fetch(ASSET_URL)
                    try:
                        self.assertEqual(fetched.read(), body)
                        self.assertIsNone(fetched.headers.get("Content-Encoding"))
                    finally:
                        fetched.close()
                    self.assertTrue(stream.closed)

    def test_missing_or_false_content_length_cannot_bypass_limit(self):
        for content_length in (None, "0", "1", str(BODY_LIMIT)):
            with self.subTest(content_length=content_length):
                stream = BoundedReadStream(b"a" * (BODY_LIMIT * 10))
                headers = {"Content-Type": "text/css"}
                if content_length is not None:
                    headers["Content-Length"] = content_length
                response = URLFetcherResponse(ASSET_URL, stream, headers)
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    self.assertRaisesMessage(ValueError, "maximum size"),
                ):
                    ReportURLFetcher().fetch(ASSET_URL)
                self.assertTrue(stream.closed)
                self.assertLessEqual(stream.bytes_read, BODY_LIMIT + 1)

    def test_deflate_does_not_use_weasyprint_unbounded_decompressor(self):
        body = b"a" * (BODY_LIMIT * 100)
        for encoding in ("deflate", "raw-deflate"):
            with self.subTest(encoding=encoding):
                encoded, headers = encoded_response(body, encoding)
                stream = BoundedReadStream(encoded)
                response = URLFetcherResponse(
                    ASSET_URL, stream, {"Content-Type": "text/css", **headers}
                )
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    patch(
                        "weasyprint.urls.zlib.decompress",
                        side_effect=AssertionError("Unbounded deflate allocation"),
                    ) as unbounded_decompress,
                ):
                    with self.assertRaisesMessage(ValueError, "maximum size"):
                        ReportURLFetcher().fetch(ASSET_URL)
                    unbounded_decompress.assert_not_called()
                self.assertTrue(stream.closed)

    def test_compressed_resources_limit_each_decompression_allocation(self):
        make_decoder = zlib.decompressobj
        test_case = self

        class BoundedDecoder:
            def __init__(self, *args, **kwargs):
                self.decoder = make_decoder(*args, **kwargs)

            def decompress(self, data, max_length=0):
                test_case.assertGreater(max_length, 0)
                test_case.assertLessEqual(max_length, BODY_LIMIT + 1)
                return self.decoder.decompress(data, max_length)

            def flush(self, *args, **kwargs):
                # zlib's flush(length) argument is an initial buffer size, not a cap.
                test_case.assertTrue(self.decoder.eof)
                return self.decoder.flush(*args, **kwargs)

            def __getattr__(self, name):
                return getattr(self.decoder, name)

        for encoding in ("gzip", "deflate", "raw-deflate"):
            with self.subTest(encoding=encoding):
                encoded, headers = encoded_response(b"a" * (BODY_LIMIT * 100), encoding)
                stream = BoundedReadStream(encoded)
                response = URLFetcherResponse(
                    ASSET_URL, stream, {"Content-Type": "text/css", **headers}
                )
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    patch("zlib.decompressobj", side_effect=BoundedDecoder),
                    patch(
                        "zlib.decompress",
                        side_effect=AssertionError("Unbounded deflate allocation"),
                    ),
                    patch(
                        "gzip.decompress",
                        side_effect=AssertionError("Unbounded gzip allocation"),
                    ),
                    self.assertRaisesMessage(ValueError, "maximum size"),
                ):
                    ReportURLFetcher().fetch(ASSET_URL)
                self.assertTrue(stream.closed)

    def test_gzip_concatenated_members_cannot_hide_oversized_output(self):
        body = gzip.compress(b"a" * BODY_LIMIT) + gzip.compress(b"b")
        stream = BoundedReadStream(body)
        response = URLFetcherResponse(
            ASSET_URL,
            stream,
            {"Content-Type": "text/css", "Content-Encoding": "gzip"},
        )
        with (
            patch(
                "urllib.request.OpenerDirector.open",
                autospec=True,
                return_value=response,
            ),
            self.assertRaises(ValueError),
        ):
            ReportURLFetcher().fetch(ASSET_URL)
        self.assertTrue(stream.closed)

    def test_resource_stream_is_closed_when_transport_read_fails(self):
        stream = BoundedReadStream(b"unused")
        response = URLFetcherResponse(ASSET_URL, stream, {"Content-Type": "text/css"})
        with (
            patch(
                "urllib.request.OpenerDirector.open",
                autospec=True,
                return_value=response,
            ),
            patch.object(stream, "read", side_effect=OSError("Transport read failed")),
            self.assertRaisesMessage(OSError, "Transport read failed"),
        ):
            ReportURLFetcher().fetch(ASSET_URL)
        self.assertTrue(stream.closed)

    def test_oversized_compressed_input_is_rejected_before_decompression(self):
        wire_limit = BODY_LIMIT + 64 * 1024
        for encoding in ("gzip", "deflate"):
            with self.subTest(encoding=encoding):
                stream = BoundedReadStream(b"a" * (wire_limit + 1))
                response = URLFetcherResponse(
                    ASSET_URL,
                    stream,
                    {"Content-Type": "text/css", "Content-Encoding": encoding},
                )
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    patch(
                        "care.emr.reports.renderer.generators.weasyprint_generator.GzipFile",
                        side_effect=AssertionError("Oversized input reached decoder"),
                    ) as decode_gzip,
                    patch(
                        "zlib.decompressobj",
                        side_effect=AssertionError("Oversized input reached decoder"),
                    ) as decode_deflate,
                    self.assertRaisesMessage(ValueError, "maximum size"),
                ):
                    ReportURLFetcher().fetch(ASSET_URL)
                decode_gzip.assert_not_called()
                decode_deflate.assert_not_called()
                self.assertLessEqual(stream.bytes_read, wire_limit + 1)
                self.assertTrue(stream.closed)

    def test_truncated_or_unsupported_compression_is_rejected_and_closed(self):
        for encoding in ("gzip", "deflate", "raw-deflate"):
            with self.subTest(truncated=encoding):
                body, headers = encoded_response(b"p { color: red; }", encoding)
                stream = BoundedReadStream(body[:-1])
                response = URLFetcherResponse(
                    ASSET_URL, stream, {"Content-Type": "text/css", **headers}
                )
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    self.assertRaises((ValueError, EOFError, zlib.error)),
                ):
                    ReportURLFetcher().fetch(ASSET_URL)
                self.assertTrue(stream.closed)

        for encoding in ("br", "gzip, deflate", "gzip, gzip", ("gzip", "deflate")):
            with self.subTest(unsupported=encoding):
                stream = BoundedReadStream(b"p { color: red; }")
                response = URLFetcherResponse(
                    ASSET_URL, stream, {"Content-Type": "text/css"}
                )
                for value in encoding if isinstance(encoding, tuple) else (encoding,):
                    response.headers.add_header("Content-Encoding", value)
                with (
                    patch(
                        "urllib.request.OpenerDirector.open",
                        autospec=True,
                        return_value=response,
                    ),
                    self.assertRaisesMessage(ValueError, "content encoding"),
                ):
                    ReportURLFetcher().fetch(ASSET_URL)
                self.assertEqual(stream.bytes_read, 0)
                self.assertTrue(stream.closed)

    def test_nonpositive_limit_is_rejected_before_opening_transport(self):
        for limit in (0, -1):
            with (
                self.subTest(limit=limit),
                override_settings(REPORT_MAX_RESOURCE_SIZE_BYTES=limit),
                patch("urllib.request.OpenerDirector.open", autospec=True) as open_url,
                self.assertRaisesMessage(ValueError, "must be positive"),
            ):
                ReportURLFetcher().fetch(ASSET_URL)
            open_url.assert_not_called()
