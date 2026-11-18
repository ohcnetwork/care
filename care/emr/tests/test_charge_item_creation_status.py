from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.utils.tests.base import CareAPITestBase


class ChargeItemCreationStatusTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.account = baker.make(
            "emr.Account",
            facility=self.facility,
            patient=self.patient,
            status="active",
            billing_status="open",
        )
        self.client.force_authenticate(user=self.user)
        kwargs = {"facility_external_id": self.facility.external_id}
        self.create_url = reverse("charge_item-list", kwargs=kwargs)
        self.upsert_url = reverse("charge_item-upsert", kwargs=kwargs)

    def charge_data(self, item_status=ChargeItemStatusOptions.billable.value):
        return {
            "patient": str(self.patient.external_id),
            "account": str(self.account.external_id),
            "title": "Consultation",
            "status": item_status,
            "quantity": "1.00",
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
        }

    def make_charge_item(self, *, attached=False):
        item = baker.make(
            ChargeItem,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            title="Consultation",
            status=ChargeItemStatusOptions.billable.value,
            quantity="1.00",
            unit_price_components=self.charge_data()["unit_price_components"],
            total_price_components=[
                {"monetary_component_type": "base", "amount": "100.00"}
            ],
            total_price="100.00",
        )
        if attached:
            invoice = baker.make(
                Invoice,
                facility=self.facility,
                patient=self.patient,
                account=self.account,
                status="draft",
                charge_items=[item.pk],
            )
            item.status = ChargeItemStatusOptions.billed.value
            item.paid_invoice = invoice
            item.save(update_fields=["status", "paid_invoice"])
        return item

    def item_url(self, item):
        return reverse(
            "charge_item-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": item.external_id,
            },
        )

    def update_data(self, title="Updated consultation"):
        return {
            "title": title,
            "quantity": "1.00",
            "unit_price_components": self.charge_data()["unit_price_components"],
        }

    def assert_status_spec_error(self, data):
        self.assertTrue(
            any(
                error["type"] == "enum" and error["loc"] == ["status"]
                for error in data["errors"]
            ),
            data,
        )

    def assert_status_transition_error(self, data):
        self.assertTrue(
            any(
                error["type"] == "validation_error"
                and error["msg"]
                == "Billed and paid statuses can only be set by an invoice"
                for error in data["errors"]
            ),
            data,
        )

    def test_create_rejects_invoice_managed_statuses(self):
        for item_status in (
            ChargeItemStatusOptions.billed.value,
            ChargeItemStatusOptions.paid.value,
        ):
            with self.subTest(status=item_status):
                response = self.client.post(
                    self.create_url, self.charge_data(item_status), format="json"
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_status_spec_error(response.data)
                self.assertFalse(ChargeItem.objects.exists())
                self.assertFalse(Invoice.objects.exists())

    def test_upsert_rolls_back_creation_when_later_status_is_invoice_managed(self):
        for item_status in (
            ChargeItemStatusOptions.billed.value,
            ChargeItemStatusOptions.paid.value,
        ):
            with self.subTest(status=item_status):
                response = self.client.post(
                    self.upsert_url,
                    {
                        "datapoints": [
                            self.charge_data(),
                            self.charge_data(item_status),
                        ]
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_status_spec_error(response.data[1])
                self.assertFalse(ChargeItem.objects.exists())
                self.assertFalse(Invoice.objects.exists())

    def test_create_accepts_billable_status_without_an_invoice(self):
        response = self.client.post(self.create_url, self.charge_data(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = ChargeItem.objects.get(external_id=response.data["id"])
        self.assertEqual(item.status, ChargeItemStatusOptions.billable.value)
        self.assertIsNone(item.paid_invoice_id)
        self.assertIsNone(item.paid_on)
        self.assertFalse(Invoice.objects.exists())

    def test_update_rejects_transitions_into_invoice_managed_statuses(self):
        for attached in (False, True):
            item = self.make_charge_item(attached=attached)
            original_status = item.status
            original_invoice_id = item.paid_invoice_id
            for method in (self.client.put, self.client.patch):
                for item_status in ("billed", "paid"):
                    if item_status == original_status:
                        continue
                    with self.subTest(
                        attached=attached,
                        method=method.__name__,
                        status=item_status,
                    ):
                        response = method(
                            self.item_url(item),
                            {**self.update_data(), "status": item_status},
                            format="json",
                        )

                        self.assertEqual(
                            response.status_code, status.HTTP_400_BAD_REQUEST
                        )
                        self.assert_status_transition_error(response.data)
                        item.refresh_from_db()
                        self.assertEqual(item.title, "Consultation")
                        self.assertEqual(item.status, original_status)
                        self.assertEqual(item.paid_invoice_id, original_invoice_id)

    def test_update_accepts_unchanged_billed_status_on_draft_invoice(self):
        item = self.make_charge_item(attached=True)
        invoice_id = item.paid_invoice_id
        for method in (self.client.put, self.client.patch):
            with self.subTest(method=method.__name__):
                response = method(
                    self.item_url(item),
                    {**self.update_data(), "status": "billed"},
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["status"], "billed")
                item.refresh_from_db()
                self.assertEqual(item.title, "Updated consultation")
                self.assertEqual(item.status, "billed")
                self.assertEqual(item.paid_invoice_id, invoice_id)
                self.assertEqual(
                    Invoice.objects.get(pk=invoice_id).charge_items, [item.pk]
                )

    def test_upsert_rolls_back_edits_when_later_status_is_invoice_managed(self):
        for item_status in ("billed", "paid"):
            with self.subTest(status=item_status):
                first = self.make_charge_item()
                second = self.make_charge_item()
                response = self.client.post(
                    self.upsert_url,
                    {
                        "datapoints": [
                            {"id": str(first.external_id), **self.update_data()},
                            {
                                "id": str(second.external_id),
                                **self.update_data(),
                                "status": item_status,
                            },
                        ]
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_status_transition_error(response.data[1])
                for item in (first, second):
                    item.refresh_from_db()
                    self.assertEqual(item.title, "Consultation")
                    self.assertEqual(item.status, "billable")
                    self.assertIsNone(item.paid_invoice_id)

    def test_null_update_status_preserves_billed_status_and_invoice(self):
        item = self.make_charge_item(attached=True)
        invoice_id = item.paid_invoice_id

        response = self.client.put(
            self.item_url(item),
            {**self.update_data(), "status": None},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "billed")
        item.refresh_from_db()
        self.assertEqual(item.title, "Updated consultation")
        self.assertEqual(item.status, "billed")
        self.assertEqual(item.paid_invoice_id, invoice_id)
        self.assertEqual(Invoice.objects.get(pk=invoice_id).charge_items, [item.pk])

    def test_upsert_can_edit_billed_draft_item_with_or_without_current_status(self):
        item = self.make_charge_item(attached=True)
        invoice_id = item.paid_invoice_id

        for status_data in ({}, {"status": "billed"}):
            with self.subTest(status=status_data):
                response = self.client.post(
                    self.upsert_url,
                    {
                        "datapoints": [
                            {
                                "id": str(item.external_id),
                                **self.update_data(),
                                **status_data,
                            }
                        ]
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data[0]["status"], "billed")
                item.refresh_from_db()
                self.assertEqual(item.title, "Updated consultation")
                self.assertEqual(item.status, "billed")
                self.assertEqual(item.paid_invoice_id, invoice_id)
                self.assertEqual(
                    Invoice.objects.get(pk=invoice_id).charge_items, [item.pk]
                )

    def test_upsert_accepts_billable_creation(self):
        response = self.client.post(
            self.upsert_url,
            {"datapoints": [self.charge_data()]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = ChargeItem.objects.get(external_id=response.data[0]["id"])
        self.assertEqual(item.status, ChargeItemStatusOptions.billable.value)
        self.assertIsNone(item.paid_invoice_id)
        self.assertIsNone(item.paid_on)
