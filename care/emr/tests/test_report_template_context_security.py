from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from jinja2.exceptions import SecurityError, UndefinedError

from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import SingleUserIdContextBuilder
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.users.models import User


class ReportRowContext(QuerysetContextBuilder):
    name = Field(preview_value="Preview row")


class NestedReportContext(SingleObjectContextBuilder):
    name = Field(preview_value="Preview name")


class ReportDataContext(SingleObjectContextBuilder):
    name = Field(preview_value="Preview name")
    details = Field(preview_value={"label": "Preview label", "enabled": False})
    nested = Field(target_context=NestedReportContext)

    @property
    def undeclared_property(self):
        self.context.mutate()
        return self.context.password


class ReportTemplateContextSecurityTests(SimpleTestCase):
    def setUp(self):
        self.engine = TemplateEngine()
        self.user = User(
            id=1,
            username="template-author",
            first_name="Template",
            last_name="Author",
            password="private-password-hash",
            totp_secret="private-totp-secret",
        )
        self.current_user = SingleUserIdContextBuilder(context=self.user)
        self.context = {"current_user": self.current_user}

    def test_declared_user_fields_are_still_available(self):
        result = self.engine.render(
            "{{ current_user.full_name }}:{{ current_user.id }}", self.context
        )
        self.assertEqual(result, "Template Author:1")

    def test_model_traversal_and_builder_helpers_are_blocked(self):
        templates = [
            "{{ current_user.context.password }}",
            "{{ current_user.context.totp_secret }}",
            "{{ current_user.context.auth_token.key }}",
            "{{ current_user._context.password }}",
            "{{ current_user.parent_context.password }}",
            "{{ current_user._parent_context.password }}",
            "{{ current_user.get_context().password }}",
            "{{ current_user.get_iterable([]) }}",
            "{{ current_user.filterset_class }}",
            "{{ current_user['context'].password }}",
            "{{ (current_user|attr('context')).password }}",
            "{{ (current_user|attr('_context')).password }}",
            "{{ (current_user|attr('get_context'))().password }}",
            "{{ [current_user]|map(attribute='context.password')|join }}",
            "{{ [current_user]|selectattr('context')|list }}",
            "{{ '{0.context.password}'.format(current_user) }}",
        ]
        for source in templates:
            with (
                self.subTest(source=source),
                self.assertRaises((SecurityError, UndefinedError)),
            ):
                self.engine.render(source, self.context)

    def test_nested_contexts_expose_only_declared_fields(self):
        data = SimpleNamespace(name="Report name", details={})
        report = ReportDataContext(context=data)
        self.assertEqual(
            self.engine.render("{{ report.nested.name }}", {"report": report}),
            "Report name",
        )
        for attribute in ("context", "_context", "parent_context", "_parent_context"):
            with (
                self.subTest(attribute=attribute),
                self.assertRaises((SecurityError, UndefinedError)),
            ):
                self.engine.render(
                    "{{ report.nested." + attribute + " }}", {"report": report}
                )

    def test_undeclared_properties_and_mutating_helpers_never_execute(self):
        data = SimpleNamespace(
            name="Report name",
            details={},
            password="private-password-hash",
            mutate=Mock(),
            set_organization_cache=Mock(),
            sync_organization_cache=Mock(),
        )
        report = ReportDataContext(context=data)
        for source in (
            "{{ report.undeclared_property }}",
            "{{ report.context.set_organization_cache() }}",
            "{{ report.context.sync_organization_cache() }}",
            "{{ report.get_context().mutate() }}",
        ):
            with (
                self.subTest(source=source),
                self.assertRaises((SecurityError, UndefinedError)),
            ):
                self.engine.render(source, {"report": report})
        data.mutate.assert_not_called()
        data.set_organization_cache.assert_not_called()
        data.sync_organization_cache.assert_not_called()

    def test_queryset_iteration_and_documented_filter_still_work(self):
        rows = ReportRowContext(
            context=[SimpleNamespace(name="First"), SimpleNamespace(name="Second")]
        )
        self.assertEqual(
            self.engine.render(
                "{% for row in rows.filter(limit=1) %}{{ row.name }}{% endfor %}",
                {"rows": rows},
            ),
            "First",
        )
        self.assertEqual(
            self.engine.render(
                "{% for row in rows %}{{ row.name }};{% endfor %}", {"rows": rows}
            ),
            "First;Second;",
        )
        for source in (
            "{{ rows._filter() }}",
            "{{ rows.perform_extra_filters([]) }}",
            "{{ (rows|first).context }}",
        ):
            with (
                self.subTest(source=source),
                self.assertRaises((SecurityError, UndefinedError)),
            ):
                self.engine.render(source, {"rows": rows})

    def test_json_fields_remain_readable_and_cannot_be_mutated(self):
        details = {"label": "Visible label", "values": [{"value": 123}]}
        report = ReportDataContext(context=SimpleNamespace(details=details))
        self.assertEqual(
            self.engine.render(
                "{{ report.details.label }}:{{ report.details['values'][0].value }}",
                {"report": report},
            ),
            "Visible label:123",
        )
        for source in (
            "{{ report.details.update(label='changed') }}",
            "{{ report.details['values'].append('changed') }}",
            "{{ report.details['values'][0].clear() }}",
        ):
            with (
                self.subTest(source=source),
                self.assertRaises((SecurityError, UndefinedError)),
            ):
                self.engine.render(source, {"report": report})
        self.assertEqual(
            details, {"label": "Visible label", "values": [{"value": 123}]}
        )

    def test_objects_and_callables_hidden_in_json_fields_are_rejected(self):
        for value in (
            {"peer": self.user},
            [self.user],
            {"nested": [{"mutate": Mock()}]},
        ):
            report = ReportDataContext(context=SimpleNamespace(details=value))
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.engine.render("{{ report.details }}", {"report": report})

    def test_raw_models_cannot_be_added_to_the_render_context(self):
        with self.assertRaises(TypeError):
            self.engine.render("{{ user.password }}", {"user": self.user})

    def test_custom_nested_context_cannot_return_a_raw_model(self):
        class UnsafeNestedContext(SingleObjectContextBuilder):
            nested = Field(target_context=lambda parent, attr, **kwargs: parent)

        report = UnsafeNestedContext(context=self.user)
        with self.assertRaises(TypeError):
            self.engine.render("{{ report.nested.password }}", {"report": report})

    def test_preview_and_standard_filters_still_work(self):
        report = ReportDataContext(is_preview=True)
        self.assertEqual(
            self.engine.render(
                "{{ report.name }}:{{ report.details.label }}:{{ report.nested.name }}",
                {"report": report},
            ),
            "Preview name:Preview label:Preview name",
        )
        self.assertEqual(
            self.engine.render(
                "{{ birthday|date }}:{{ amount|currency }}:{{ data.get('label') }}",
                {
                    "birthday": date(2026, 11, 2),
                    "amount": Decimal("1234.50"),
                    "data": {"label": "Visible label"},
                },
            ),
            "02/11/2026:₹1,234.50:Visible label",
        )
