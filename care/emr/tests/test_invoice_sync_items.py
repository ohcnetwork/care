from decimal import Decimal

from django.test import TestCase, override_settings
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items


@override_settings(
    ACCOUNTING_PRECISION=2,
    ACCOUNTING_ROUNDING_METHOD="care.utils.rounding.RoundingHalfUp",
    INVOICE_FINAL_AMOUNT_PRECISION=0,
    INVOICE_FINAL_AMOUNT_ROUNDING_METHOD="care.utils.rounding.RoundingHalfUp",
)
class InvoiceSyncItemsTests(TestCase):
    def setUp(self):
        user = baker.make("users.User")
        facility = baker.make("facility.Facility", created_by=user)
        patient = baker.make("emr.Patient")
        self.account = baker.make(
            "emr.Account",
            facility=facility,
            patient=patient,
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )
        self.invoice = baker.make(
            "emr.Invoice",
            facility=self.account.facility,
            patient=self.account.patient,
            account=self.account,
            status=InvoiceStatusOptions.draft.value,
        )

    def add_charge_item(self, components, total_price):
        charge_item = baker.make(
            "emr.ChargeItem",
            facility=self.account.facility,
            patient=self.account.patient,
            account=self.account,
            status=ChargeItemStatusOptions.billed.value,
            quantity=Decimal(1),
            unit_price_components=components,
            total_price_components=components,
            total_price=Decimal(total_price),
        )
        self.invoice.charge_items.append(charge_item.id)

    def test_rounds_net_after_summing_charge_items_and_price_components(self):
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "10.123456"},
                {"monetary_component_type": "surcharge", "amount": "0.234567"},
                {"monetary_component_type": "discount", "amount": "0.012345"},
                {"monetary_component_type": "tax", "amount": "0.987654"},
            ],
            "11.333332",
        )
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "2.345678"},
                {"monetary_component_type": "tax", "amount": "0.123456"},
            ],
            "2.469134",
        )

        sync_invoice_items(self.invoice)
        self.invoice.save()
        self.invoice.refresh_from_db()

        self.assertEqual(self.invoice.total_net, Decimal("12.69"))
        self.assertEqual(self.invoice.total_gross, Decimal(14))

    @override_settings(
        INVOICE_FINAL_AMOUNT_PRECISION=2,
        INVOICE_FINAL_AMOUNT_ROUNDING_METHOD="care.utils.rounding.RoundingDown",
    )
    def test_final_rounding_settings_apply_only_to_gross(self):
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "10.987654"},
                {"monetary_component_type": "tax", "amount": "0.009876"},
            ],
            "10.997530",
        )

        sync_invoice_items(self.invoice)
        self.invoice.save()
        self.invoice.refresh_from_db()

        self.assertEqual(self.invoice.total_net, Decimal("10.99"))
        self.assertEqual(self.invoice.total_gross, Decimal("10.99"))

    @override_settings(
        ACCOUNTING_PRECISION=3,
        ACCOUNTING_ROUNDING_METHOD="care.utils.rounding.RoundingDown",
    )
    def test_net_uses_accounting_rounding_settings(self):
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "10.987654"},
                {"monetary_component_type": "tax", "amount": "0.009876"},
            ],
            "10.997530",
        )

        sync_invoice_items(self.invoice)
        self.invoice.save()
        self.invoice.refresh_from_db()

        self.assertEqual(self.invoice.total_net, Decimal("10.987"))
        self.assertEqual(self.invoice.total_gross, Decimal(11))

    def test_rounds_net_and_gross_independently_at_rounding_boundaries(self):
        for is_refund, amount, expected_net in (
            (False, "0.494999", "0.49"),
            (False, "0.495000", "0.50"),
            (False, "-0.000001", "0.00"),
            (True, "-0.494999", "-0.49"),
            (True, "-0.495000", "-0.50"),
            (True, "-0.000001", "0.00"),
        ):
            with self.subTest(is_refund=is_refund, amount=amount):
                self.invoice.is_refund = is_refund
                self.invoice.charge_items = []
                self.add_charge_item(
                    [{"monetary_component_type": "base", "amount": amount}],
                    amount,
                )

                sync_invoice_items(self.invoice)
                self.invoice.save()
                self.invoice.refresh_from_db()

                self.assertEqual(self.invoice.total_net, Decimal(expected_net))
                self.assertEqual(self.invoice.total_gross, Decimal(0))

    def test_refund_rounds_negative_net_to_accounting_precision(self):
        self.invoice.is_refund = True
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "-10.123456"},
                {"monetary_component_type": "tax", "amount": "-1.234567"},
            ],
            "-11.358023",
        )

        sync_invoice_items(self.invoice)
        self.invoice.save()
        self.invoice.refresh_from_db()

        self.assertEqual(self.invoice.total_net, Decimal("-10.12"))
        self.assertEqual(self.invoice.total_gross, Decimal(-11))

    def test_rejects_negative_net_when_gross_rounds_to_zero_without_refund(self):
        self.add_charge_item(
            [{"monetary_component_type": "base", "amount": "-0.01"}],
            "-0.01",
        )

        with self.assertRaisesRegex(
            ValidationError, "A Refund Invoice is required for negative values"
        ):
            sync_invoice_items(self.invoice)

    def test_rejects_negative_net_when_tax_makes_gross_positive(self):
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "-0.01"},
                {"monetary_component_type": "tax", "amount": "1.00"},
            ],
            "0.99",
        )

        with self.assertRaisesRegex(
            ValidationError, "A Refund Invoice is required for negative values"
        ):
            sync_invoice_items(self.invoice)

    def test_rejects_negative_gross_when_net_rounds_to_zero(self):
        self.add_charge_item(
            [
                {"monetary_component_type": "base", "amount": "0.000001"},
                {"monetary_component_type": "tax", "amount": "-0.500001"},
            ],
            "-0.500000",
        )

        with self.assertRaisesRegex(
            ValidationError, "A Refund Invoice is required for negative values"
        ):
            sync_invoice_items(self.invoice)
