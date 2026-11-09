from datetime import UTC, datetime
from uuid import uuid4

from django.test import SimpleTestCase
from pydantic import ValidationError

from care.emr.models.charge_item import ChargeItem
from care.emr.resources.charge_item.spec import (
    ChargeItemReadSpec,
    ChargeItemStatusOptions,
    ChargeItemUpdateSpec,
    ChargeItemWriteSpec,
)


class ChargeItemStatusSpecTests(SimpleTestCase):
    allowed_statuses = {"billable", "not_billable", "aborted", "entered_in_error"}

    def data(self, spec):
        data = {
            "title": "Consultation",
            "quantity": "1.00",
            "unit_price_components": [],
        }
        if spec is ChargeItemWriteSpec:
            data["patient"] = uuid4()
        return data

    def status_choices(self, spec):
        schema = spec.model_json_schema()

        def choices(field):
            if "$ref" in field:
                return choices(schema["$defs"][field["$ref"].rsplit("/", 1)[-1]])
            if "enum" in field:
                return set(field["enum"])
            return set().union(*(choices(option) for option in field.get("anyOf", [])))

        return choices(schema["properties"]["status"])

    def test_creation_spec_rejects_invoice_managed_statuses(self):
        for item_status in (
            "billed",
            "paid",
            ChargeItemStatusOptions.billed,
            ChargeItemStatusOptions.paid,
        ):
            with self.subTest(status=item_status), self.assertRaises(ValidationError):
                ChargeItemWriteSpec(
                    **self.data(ChargeItemWriteSpec), status=item_status
                )

    def test_update_spec_parses_invoice_managed_statuses_for_transition_validation(
        self,
    ):
        for item_status in (
            "billed",
            "paid",
            ChargeItemStatusOptions.billed,
            ChargeItemStatusOptions.paid,
        ):
            with self.subTest(status=item_status):
                request = ChargeItemUpdateSpec(
                    **self.data(ChargeItemUpdateSpec), status=item_status
                )
                self.assertEqual(request.status, item_status)

    def test_request_specs_accept_user_settable_statuses(self):
        for spec in (ChargeItemWriteSpec, ChargeItemUpdateSpec):
            for item_status in self.allowed_statuses:
                with self.subTest(spec=spec.__name__, status=item_status):
                    request = spec(**self.data(spec), status=item_status)
                    self.assertEqual(request.status, item_status)

    def test_creation_schema_only_offers_user_settable_statuses(self):
        self.assertEqual(
            self.status_choices(ChargeItemWriteSpec), self.allowed_statuses
        )

    def test_update_schema_includes_existing_invoice_managed_statuses(self):
        self.assertEqual(
            self.status_choices(ChargeItemUpdateSpec),
            {item_status.value for item_status in ChargeItemStatusOptions},
        )

    def test_read_spec_includes_invoice_managed_statuses(self):
        self.assertEqual(
            self.status_choices(ChargeItemReadSpec),
            {item_status.value for item_status in ChargeItemStatusOptions},
        )
        now = datetime.now(UTC)
        for item_status in ("billed", "paid"):
            with self.subTest(status=item_status):
                item = ChargeItemReadSpec(
                    **self.data(ChargeItemReadSpec),
                    status=item_status,
                    total_price_components=[],
                    total_price="1.00",
                    charge_item_definition={},
                    created_date=now,
                    modified_date=now,
                )
                self.assertEqual(item.model_dump(mode="json")["status"], item_status)

    def test_update_without_status_preserves_the_existing_status(self):
        for item_status in ("billed", "paid"):
            with self.subTest(status=item_status):
                item = ChargeItem(status=item_status, title="Original consultation")
                request = ChargeItemUpdateSpec(**self.data(ChargeItemUpdateSpec))

                request.de_serialize(obj=item)

                self.assertEqual(item.status, item_status)
                self.assertEqual(item.title, "Consultation")
                self.assertNotIn("status", request.model_dump(exclude_defaults=True))

    def test_null_update_status_does_not_clear_the_existing_status(self):
        item = ChargeItem(status="billed", title="Original consultation")
        request = ChargeItemUpdateSpec(**self.data(ChargeItemUpdateSpec), status=None)

        request.de_serialize(obj=item)

        self.assertEqual(item.status, "billed")
        self.assertNotIn("status", request.model_dump(exclude_defaults=True))

    def test_creation_still_requires_a_status(self):
        with self.assertRaises(ValidationError):
            ChargeItemWriteSpec(**self.data(ChargeItemWriteSpec))
