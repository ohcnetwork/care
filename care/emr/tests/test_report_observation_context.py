from types import SimpleNamespace

from django.test import SimpleTestCase

from care.emr.reports.context_builder.data_points.observation import (
    ObservationContextBuilder,
)
from care.emr.reports.renderer.template_engine import TemplateEngine


class ReportObservationContextTests(SimpleTestCase):
    def setUp(self):
        self.engine = TemplateEngine()

    @staticmethod
    def context(value):
        observation = SimpleNamespace(value=value, component=[{"value": value}])
        return {"observation": ObservationContextBuilder(context=observation)}

    def test_zero_observation_and_component_values_render_with_their_unit(self):
        template = (
            "{% if observation.value.value %}"
            "{{ observation.value.value }} {{ observation.value.unit }}"
            "{% else %}missing{% endif %}|"
            "{% for component in observation.component %}"
            "{% if component.value.value %}"
            "{{ component.value.value }} {{ component.value.unit }}"
            "{% else %}missing{% endif %}"
            "{% endfor %}"
        )

        result = self.engine.render(
            template, self.context({"value": 0, "unit": {"code": "mg/dL"}})
        )

        self.assertEqual(result, "0 mg/dL|0 mg/dL")

    def test_null_and_empty_observation_and_component_values_render_empty(self):
        template = (
            "{{ observation.value.value }}|"
            "{% for component in observation.component %}"
            "{{ component.value.value }}{% endfor %}"
        )
        for value in (None, {}, {"value": None}, {"value": ""}):
            with self.subTest(value=value):
                self.assertEqual(self.engine.render(template, self.context(value)), "|")

    def test_nonzero_values_and_units_are_unchanged(self):
        template = (
            "{{ observation.value.value }} {{ observation.value.unit }}|"
            "{% for component in observation.component %}"
            "{{ component.value.value }} {{ component.value.unit }}"
            "{% endfor %}"
        )

        result = self.engine.render(
            template, self.context({"value": 12.5, "unit": {"code": "mg/dL"}})
        )

        self.assertEqual(result, "12.5 mg/dL|12.5 mg/dL")
