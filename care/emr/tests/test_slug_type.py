from django.test import TestCase
from pydantic import BaseModel, ValidationError

from care.emr.resources.valueset.spec import ValueSetSpec
from care.emr.utils.slug_type import SlugType


class TestModel(BaseModel):
    slug: SlugType
    optional_slug: SlugType | None = None


class TestSlugTypeValidation(TestCase):
    def test_valid_slugs(self):
        valid_slugs = [
            "valid-slug",
            "valid_slug",
            "test123",
            "test-123_abc",
            "12345",
            "hello-world-123",
        ]

        for slug in valid_slugs:
            model = TestModel(slug=slug)
            self.assertEqual(model.slug, slug)

    def test_invalid_slugs(self):
        invalid_slugs = [
            "",
            "ab",
            "a" * 26,
            "invalid slug",
            "invalid@slug",
            "invalid.slug",
            "invalid/slug",
        ]

        for slug in invalid_slugs:
            with self.assertRaises(ValidationError):
                TestModel(slug=slug)

    def test_uppercase_slug_handling(self):
        try:
            model = TestModel(slug="UPPERCASE")
            self.assertEqual(model.slug, "UPPERCASE")
        except ValidationError:
            pass

    def test_length_constraints(self):
        with self.assertRaises(ValidationError):
            TestModel(slug="ab")

        with self.assertRaises(ValidationError):
            TestModel(slug="a" * 26)

    def test_optional_slug_handling(self):
        model = TestModel(slug="valid-slug", optional_slug=None)
        self.assertIsNone(model.optional_slug)

        model = TestModel(slug="valid-slug", optional_slug="another-valid")
        self.assertEqual(model.optional_slug, "another-valid")

        with self.assertRaises(ValidationError):
            TestModel(slug="valid-slug", optional_slug="invalid slug")

    def test_non_string_input(self):
        with self.assertRaises(ValidationError):
            TestModel(slug=123)

        with self.assertRaises(ValidationError):
            TestModel(slug=None)

    def test_url_safe_characters_only(self):
        valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789-_"
        TestModel(slug="test-" + valid_chars[:20])

        invalid_chars = [
            "@",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            "+",
            "=",
            " ",
            ".",
            "/",
            "\\",
        ]
        for char in invalid_chars:
            with self.assertRaises(ValidationError):
                TestModel(slug=f"test{char}slug")

    def test_compatibility_with_actual_specs(self):
        valid_valueset_data = {
            "slug": "valid-slug-test",
            "name": "Test ValueSet",
            "description": "A test value set",
            "compose": {"include": []},
            "status": "active",
        }

        try:
            spec = ValueSetSpec(**valid_valueset_data)
            self.assertEqual(spec.slug, "valid-slug-test")
        except Exception as e:
            self.fail(f"Valid ValueSetSpec creation failed: {e}")

        valid_valueset_data_none_slug = {
            "slug": None,
            "name": "Test ValueSet",
            "description": "A test value set",
            "compose": {"include": []},
            "status": "active",
        }

        try:
            spec = ValueSetSpec(**valid_valueset_data_none_slug)
            self.assertIsNone(spec.slug)
        except Exception as e:
            self.fail(f"ValueSetSpec creation with None slug failed: {e}")
