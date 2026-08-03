import random
from datetime import UTC, datetime
from decimal import Decimal

from django.urls import reverse
from model_bakery import baker

from care.emr.models import Account, ChargeItem, ChargeItemDefinition
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
)
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.signals.patient.facility_name_identifier import (
    FacilityPatientNameIdentifierConfig,
)
from care.emr.signals.patient.name_identifier import NameIdentifierConfig
from care.emr.signals.patient.phone_number_identifier import PhoneNumberIdentifierConfig
from care.security.permissions.invoice import InvoicePermissions
from care.utils.tests.base import CareAPITestBase


class InvoiceAPITestBase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        NameIdentifierConfig.CACHED_CONFIG = {}
        PhoneNumberIdentifierConfig.CACHED_CONFIG = {}
        FacilityPatientNameIdentifierConfig.CACHED_CONFIG = {}
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        self.account = Account.objects.create(
            facility=self.facility,
            patient=self.patient,
            name=f"Account for {self.patient.name}",
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )
        self.charge_item_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Charge Definition",
            slug=f"f-{self.facility.external_id}-test-charge-def",
            price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
        )
        self.charge_item = self.create_charge_item()
        self.url = reverse(
            "invoice-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        permissions = [
            InvoicePermissions.can_read_invoice.name,
            InvoicePermissions.can_write_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)

    def generate_invoice_data(self, **kwargs):
        data = {
            "account": self.account.external_id,
            "status": kwargs.get("status", InvoiceStatusOptions.draft.value),
            "charge_items": kwargs.get("charge_items", [self.charge_item.external_id]),
            "title": "Test Invoice",
            "number": f"INV-{random.randint(1000, 9999)}",  # noqa: S311
            "issue_date": datetime.now(UTC).isoformat(),
        }
        data.update(**kwargs)
        return data

    def create_invoice(self, **kwargs):
        return baker.make(
            "emr.Invoice",
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=kwargs.get("status", InvoiceStatusOptions.draft.value),
            charge_items=kwargs.get("charge_items", [self.charge_item.id]),
            title=kwargs.get("title", "Test Invoice"),
            number=kwargs.get("number", f"INV-{random.randint(1000, 9999)}"),  # noqa: S311
            issue_date=kwargs.get("issue_date", datetime.now(UTC).isoformat()),
        )

    def get_detail_url(self, external_id):
        return reverse(
            "invoice-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def create_charge_item(self, **kwargs):
        data = {
            "title": self.fake.sentence(nb_words=4),
            "patient": self.patient,
            "encounter": self.encounter,
            "account": self.account,
            "charge_item_definition": self.charge_item_definition,
            "facility": self.facility,
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": Decimal("1.00"),
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
            "total_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
            "total_price": Decimal("100.00"),
        }
        data.update(**kwargs)
        return ChargeItem.objects.create(**data)

    # testcases for create invoice with charge items and account

    def test_create_invoice_with_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_invoice_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["account"]["id"], str(self.account.external_id))
        self.assertEqual(response_data["status"], InvoiceStatusOptions.draft.value)
        self.assertEqual(len(response_data["charge_items"]), 1)
        self.assertEqual(
            response_data["charge_items"][0]["id"], str(self.charge_item.external_id)
        )
        self.assertEqual(
            Decimal(response_data["total_net"]), self.charge_item.total_price
        )
        self.assertEqual(
            Decimal(response_data["total_gross"]), self.charge_item.total_price
        )

    def test_create_invoice_with_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self.generate_invoice_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot write invoice")

    def test_create_invoice_with_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_invoice_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["account"]["id"], str(self.account.external_id))
        self.assertEqual(response_data["status"], InvoiceStatusOptions.draft.value)
        self.assertEqual(len(response_data["charge_items"]), 1)
        self.assertEqual(
            response_data["charge_items"][0]["id"], str(self.charge_item.external_id)
        )
        self.assertEqual(
            Decimal(response_data["total_net"]), self.charge_item.total_price
        )
        self.assertEqual(
            Decimal(response_data["total_gross"]), self.charge_item.total_price
        )

    def test_create_invoice_with_account_from_other_facility(self):
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        another_account = Account.objects.create(
            facility=self.create_facility(user=self.user),
            patient=self.patient,
            name=f"Account for {self.patient.name}",
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_invoice_data(account=str(another_account.external_id))
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Account is not associated with the facility",
        )


# class TestAttachAccountToInvoice(CareAPITestBase):
#     def setUp(self):
#         super().setUp()
#         self.user = self.create_user()
#         self.facility = self.create_facility(user=self.user)
#         self.organization = self.create_facility_organization(facility=self.facility)
#         self.patient = self.create_patient()
#         self.encounter = self.create_encounter(
#             patient=self.patient, facility=self.facility, organization=self.organization
#         )

#         self.account = Account.objects.create(
#             facility=self.facility,
#             patient=self.patient,
#             name=f"Account for {self.patient.name}",
#             status=AccountStatusOptions.active.value,
#             billing_status=AccountBillingStatusOptions.open.value,
#         )

#         self.charge_item_1 = baker.make(
#             "emr.ChargeItem",
#             facility=self.facility,
#             patient=self.patient,
#             encounter=self.encounter,
#             account=self.account,
#             status=ChargeItemStatusOptions.billable.value,
#             quantity=Decimal("1.00"),
#             unit_price_components=[{"amount": 100, "monetary_component_type": "base"}],
#             total_price_components=[{"amount": 100, "monetary_component_type": "base"}],
#             total_price=Decimal("100.00"),
#         )
#         self.charge_item_2 = baker.make(
#             "emr.ChargeItem",
#             facility=self.facility,
#             patient=self.patient,
#             encounter=self.encounter,
#             account=self.account,
#             status=ChargeItemStatusOptions.billable.value,
#             quantity=Decimal("1.00"),
#             unit_price_components=[{"amount": 200, "monetary_component_type": "base"}],
#             total_price_components=[{"amount": 200, "monetary_component_type": "base"}],
#             total_price=Decimal("200.00"),
#         )

#     def _get_url(self, invoice_external_id):
#         return reverse(
#             "invoice-attach-account-to-invoice",
#             kwargs={
#                 "facility_external_id": self.facility.external_id,
#                 "external_id": invoice_external_id,
#             },
#         )

#     def test_attach_account_to_invoice_attaches_all_billable_charge_items(self):
#         role = self.create_role_with_permissions(
#             [
#                 InvoicePermissions.can_read_invoice.name,
#                 InvoicePermissions.can_write_invoice.name,
#             ]
#         )
#         self.attach_role_facility_organization_user(self.organization, self.user, role)
#         self.client.force_authenticate(user=self.user)

#         invoice = baker.make(
#             "emr.Invoice",
#             facility=self.facility,
#             account=self.account,
#             patient=self.patient,
#             status=InvoiceStatusOptions.draft.value,
#             total_net=Decimal("0.00"),
#             total_gross=Decimal("0.00"),
#         )

#         response = self.client.post(self._get_url(invoice.external_id))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#         invoice.refresh_from_db()
#         # Assert invoice.charge_items is a proper Python list, not a queryset
#         self.assertIsInstance(invoice.charge_items, list)
#         self.assertEqual(len(invoice.charge_items), 2)
#         self.assertIn(self.charge_item_1.id, invoice.charge_items)
#         self.assertIn(self.charge_item_2.id, invoice.charge_items)

#         # Assert charge items status updated to billed and paid_invoice set
#         self.charge_item_1.refresh_from_db()
#         self.charge_item_2.refresh_from_db()
#         self.assertEqual(
#             self.charge_item_1.status, ChargeItemStatusOptions.billed.value
#         )
#         self.assertEqual(
#             self.charge_item_2.status, ChargeItemStatusOptions.billed.value
#         )
#         self.assertEqual(self.charge_item_1.paid_invoice, invoice)
#         self.assertEqual(self.charge_item_2.paid_invoice, invoice)

#     def test_attach_account_to_invoice_requires_draft_status(self):
#         role = self.create_role_with_permissions(
#             [
#                 InvoicePermissions.can_read_invoice.name,
#                 InvoicePermissions.can_write_invoice.name,
#             ]
#         )
#         self.attach_role_facility_organization_user(self.organization, self.user, role)
#         self.client.force_authenticate(user=self.user)

#         invoice = baker.make(
#             "emr.Invoice",
#             facility=self.facility,
#             account=self.account,
#             patient=self.patient,
#             status=InvoiceStatusOptions.issued.value,
#         )

#         response = self.client.post(self._get_url(invoice.external_id))
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_attach_account_to_invoice_without_permission(self):
#         # Authenticate without attaching the role with permissions to the user
#         self.client.force_authenticate(user=self.user)

#         invoice = baker.make(
#             "emr.Invoice",
#             facility=self.facility,
#             account=self.account,
#             patient=self.patient,
#             status=InvoiceStatusOptions.draft.value,
#         )

#         response = self.client.post(self._get_url(invoice.external_id))
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
