from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.resources.payment_reconciliation.spec import (
    PaymentReconciliationIssuerTypeOptions,
    PaymentReconciliationKindOptions,
    PaymentReconciliationOutcomeOptions,
    PaymentReconciliationPaymentMethodOptions,
    PaymentReconciliationStatusOptions,
    PaymentReconciliationTypeOptions,
)
from care.security.permissions.payment_reconciliation import (
    PaymentReconciliationPermissions,
)
from care.utils.tests.base import CareAPITestBase


class PaymentReconciliationAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="TestUser")
        self.superuser = self.create_super_user(username="SuperUser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            name="Test Facility Organization", facility=self.facility, org_type="root"
        )
        self.patient = self.create_patient(name="Test Patient")
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                PaymentReconciliationPermissions.can_read_payment_reconciliation.name,
                PaymentReconciliationPermissions.can_write_payment_reconciliation.name,
                PaymentReconciliationPermissions.can_destroy_payment_reconciliation.name,
            ]
        )
        self.account = self.create_account(facility=self.facility)

        self.category = baker.make(
            "emr.ResourceCategory",
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-test-category",
            title="Test Category",
            description="Test Charge Item Category",
        )

        self.charge_item_defintion = self.create_charge_item_defintion(
            facility=self.facility
        )
        self.charge_item = self.create_charge_item(
            facility=self.facility,
            account=self.account,
            charge_item_definition=self.charge_item_defintion,
        )
        self.invoice = self.create_invoice(
            facility=self.facility, account=self.account, patient=self.patient
        )
        self.base_url = self.get_base_url()

    def get_base_url(self, facility_external_id=None):
        return reverse(
            "payment_reconciliation-list",
            kwargs={
                "facility_external_id": facility_external_id
                or self.facility.external_id
            },
        )

    def get_detail_url(self, external_id, facility_external_id=None):
        return reverse(
            "payment_reconciliation-detail",
            kwargs={
                "facility_external_id": facility_external_id
                or self.facility.external_id,
                "external_id": external_id,
            },
        )

    def get_cancel_url(self, facility_external_id, external_id):
        return reverse(
            "payment_reconciliation-cancel-payment-reconciliation",
            kwargs={
                "facility_external_id": facility_external_id,
                "external_id": external_id,
            },
        )

    def create_account(self, facility, status=None, billing_status=None):
        return baker.make(
            "emr.Account",
            facility=facility,
            patient=self.patient,
            status=status or "active",
            billing_status=billing_status or "active",
        )

    def create_charge_item_defintion(self, facility):
        return baker.make(
            "emr.ChargeItemDefinition",
            facility=self.facility,
            title="Test Charge Item Definition",
            description="Test Charge Item Definition",
            slug=f"f-{self.facility.external_id}-test-charge-item-def",
            price_components=[{"amount": 500, "monetary_component_type": "base"}],
            category=self.category,
        )

    def create_charge_item(
        self, account=None, status=None, facility=None, charge_item_definition=None
    ):
        return baker.make(
            "emr.ChargeItem",
            facility=facility or self.facility,
            encounter=self.encounter,
            charge_item_definition=charge_item_definition or self.charge_item_defintion,
            account=account or self.account,
            title="Test Charge Item",
            status=status or "billed",
            quantity="1.00",
            code=None,
            unit_price_components=[{"amount": 4500, "monetary_component_type": "base"}],
            note=None,
            override_reason=None,
            total_price_components=[
                {"amount": 4500, "monetary_component_type": "base"}
            ],
            total_price="4500.00",
            service_resource="service_request",
            service_resource_id=str(self.encounter.external_id),
        )

    def create_invoice(self, account=None, facility=None, patient=None):
        return baker.make(
            "emr.Invoice",
            facility=facility or self.facility,
            account=account or self.account,
            patient=patient or self.patient,
            status="issued",
            total_net=4500,
            total_gross=4500,
            issue_date=timezone.now(),
        )

    def generate_payment_reconciliation_data(
        self,
        target_invoice=None,
        account=None,
        reconciliation_type=None,
        status=None,
        kind=None,
        issuer_type=None,
        outcome=None,
        disposition=None,
        payment_datetime=None,
        method=None,
        reference_number=None,
        authorization=None,
        tendered_amount=None,
        returned_amount=None,
        amount=None,
        note=None,
        is_credit_note=False,
    ):
        return {
            "account": account or str(self.account.external_id),
            "target_invoice": target_invoice
            if target_invoice
            else self.invoice.external_id,
            "reconciliation_type": reconciliation_type
            or PaymentReconciliationTypeOptions.payment.value,
            "status": status or PaymentReconciliationStatusOptions.active.value,
            "kind": kind or PaymentReconciliationKindOptions.deposit.value,
            "issuer_type": issuer_type
            or PaymentReconciliationIssuerTypeOptions.insurer.value,
            "outcome": outcome or PaymentReconciliationOutcomeOptions.complete.value,
            "disposition": disposition or "Test Disposition",
            "payment_datetime": payment_datetime or timezone.now().isoformat(),
            "method": method or PaymentReconciliationPaymentMethodOptions.cash.value,
            "reference_number": reference_number or "REF123456",
            "authorization": authorization or "AUTH123456",
            "tendered_amount": tendered_amount or 4500.00,
            "returned_amount": returned_amount or 0.00,
            "amount": amount or 4500.00,
            "note": note or "Test Note",
            "is_credit_note": is_credit_note,
        }

    def create_payment_reconciliation(self, facility=None, **kwargs):
        data = self.generate_payment_reconciliation_data(**kwargs)
        return baker.make(
            "emr.PaymentReconciliation", facility=facility or self.facility, **data
        )
