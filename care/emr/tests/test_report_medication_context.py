from django.test import SimpleTestCase

from care.emr.reports.context_builder.data_points.medication import (
    DosageInstructionContextBuilder,
)
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.emr.resources.medication.request.spec import DosageInstruction


class ReportDosageInstructionContextTests(SimpleTestCase):
    def setUp(self):
        self.engine = TemplateEngine()

    @staticmethod
    def dosage_instruction(dose, duration):
        # Built through the request spec, so the values are stored the same way
        # as the dosage instructions saved by the medication request API.
        return DosageInstruction.model_validate(
            {
                "as_needed_boolean": False,
                "dose_and_rate": {
                    "type": "ordered",
                    "dose_quantity": {
                        "value": dose,
                        "unit": {"code": "tablet", "display": "tablet"},
                    },
                },
                "timing": {
                    "repeat": {
                        "frequency": 1,
                        "period": 1,
                        "period_unit": "d",
                        "bounds_duration": {"value": duration, "unit": "d"},
                    },
                },
            }
        ).model_dump(mode="json")

    def render(self, instruction):
        # Same expressions as the medication table of the bundled
        # "Treatment Summary" template in data/template_fixtures.json.
        return self.engine.render(
            "{{ di.dosage or '-' }}|{{ di.duration or '-' }}",
            {"di": DosageInstructionContextBuilder(context=instruction)},
        )

    def test_whole_numbers_saved_with_a_decimal_point_render_as_whole_numbers(self):
        for value in ("2.0", "2.00", 2.0):
            with self.subTest(value=value):
                instruction = self.dosage_instruction(value, value)
                self.assertEqual(self.render(instruction), "2 tablet|2 d")

    def test_whole_numbers_and_fractions_render_unchanged(self):
        self.assertEqual(self.render(self.dosage_instruction("2", "5")), "2 tablet|5 d")
        self.assertEqual(
            self.render(self.dosage_instruction("0.5", "5")), "0.5 tablet|5 d"
        )
