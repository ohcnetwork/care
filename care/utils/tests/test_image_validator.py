import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.test import TestCase
from PIL import Image

from care.utils.models.validators import ImageSizeValidator


class HumanizeBytesTests(TestCase):
    def setUp(self):
        self.validator = ImageSizeValidator()

    def test_bytes_exact_kilobyte_boundary(self):
        # 1024 bytes is exactly 1 KB
        self.assertEqual(self.validator._humanize_bytes(1024), "1 KB")

    def test_bytes_below_kilobyte(self):
        self.assertEqual(self.validator._humanize_bytes(512), "512 B")

    def test_bytes_multiple_of_kilobyte(self):
        # 20 * 1024 = 20480 bytes = 20 KB
        # The old rstrip('.0') bug returned "2 KB" for this case
        self.assertEqual(self.validator._humanize_bytes(20 * 1024), "20 KB")

    def test_bytes_round_kilobytes(self):
        # 1000 bytes = 0.98 KB, below 1 KB so shows as B
        # The old bug would return "1" B (stripping trailing zeros from "1000.00")
        self.assertEqual(self.validator._humanize_bytes(1000), "1000 B")

    def test_bytes_megabyte(self):
        self.assertEqual(self.validator._humanize_bytes(1024 * 1024), "1 MB")

    def test_bytes_two_megabytes(self):
        self.assertEqual(self.validator._humanize_bytes(2 * 1024 * 1024), "2 MB")

    def test_bytes_fractional_kilobytes(self):
        # 1536 bytes = 1.5 KB
        self.assertEqual(self.validator._humanize_bytes(1536), "1.5 KB")


class CoverImageValidatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cover_image_validator = ImageSizeValidator(
            min_width=400,
            min_height=400,
            max_width=1024,
            max_height=1024,
            aspect_ratio=[1 / 1],
            min_size=1024,
            max_size=1024 * 1024 * 2,
        )

    def test_valid_image(self):
        image = Image.new("RGB", (400, 400))
        file = io.BytesIO()
        image.save(file, format="JPEG")
        test_file = UploadedFile(file, "test.jpg", "image/jpeg", 2048)
        self.assertIsNone(self.cover_image_validator(test_file))

    def test_invalid_image_too_small(self):
        image = Image.new("RGB", (100, 100))
        file = io.BytesIO()
        image.save(file, format="JPEG")
        test_file = UploadedFile(file, "test.jpg", "image/jpeg", 1000)
        with self.assertRaises(ValidationError) as cm:
            self.cover_image_validator(test_file)
        self.assertEqual(
            cm.exception.messages,
            [
                "Image width is less than the minimum allowed width of 400 pixels.",
                "Image height is less than the minimum allowed height of 400 pixels.",
                "Image size is less than the minimum allowed size of 1 KB.",
            ],
        )

    def test_invalid_image_too_large(self):
        image = Image.new("RGB", (2000, 2000))
        file = io.BytesIO()
        image.save(file, format="JPEG")
        test_file = UploadedFile(file, "test.jpg", "image/jpeg", 1024 * 1024 * 3)
        with self.assertRaises(ValidationError) as cm:
            self.cover_image_validator(test_file)
        self.assertEqual(
            cm.exception.messages,
            [
                "Image width is greater than the maximum allowed width of 1024 pixels.",
                "Image height is greater than the maximum allowed height of 1024 pixels.",
                "Image size is greater than the maximum allowed size of 2 MB.",
            ],
        )
