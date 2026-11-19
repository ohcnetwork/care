from django.test import SimpleTestCase

from care.emr.reports.renderer.template_engine import TemplateEngine


class TemplateCurrencyFilterTests(SimpleTestCase):
    def setUp(self):
        self.engine = TemplateEngine()

    def render_currency(self, amount):
        return self.engine.render("{{ amount|currency }}", {"amount": amount})

    def test_non_numeric_text_is_returned_unchanged(self):
        for value in ("Waived", "N/A"):
            with self.subTest(value=value):
                self.assertEqual(self.render_currency(value), value)

    def test_numeric_values_are_still_formatted(self):
        self.assertEqual(self.render_currency("1234.5"), "₹1,234.50")
