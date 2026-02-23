from decimal import Decimal

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
from care.security.permissions.location import FacilityLocationPermissions
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
                FacilityLocationPermissions.can_list_facility_locations.name,
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

        self.charge_item_definition = self.create_charge_item_definition(
            facility=self.facility
        )
        self.charge_item = self.create_charge_item(
            facility=self.facility,
            account=self.account,
            charge_item_definition=self.charge_item_definition,
        )
        self.invoice = self.create_invoice(
            facility=self.facility, account=self.account, patient=self.patient
        )
        self.base_url = self.get_base_url()
        self.facility_location = self.create_facility_location(facility=self.facility)

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

    def create_facility_location(self, facility, parent=None):
        location = baker.make(
            "emr.FacilityLocation",
            facility=facility,
            name="Test Location",
            description="Test Location",
            parent=parent,
        )
        baker.make(
            "emr.FacilityLocationOrganization",
            location=location,
            organization=self.facility_organization,
        )
        return location

    def create_account(self, facility, status=None, billing_status=None):
        return baker.make(
            "emr.Account",
            facility=facility,
            patient=self.patient,
            status=status or "active",
            billing_status=billing_status or "active",
        )

    def create_charge_item_definition(self, facility):
        return baker.make(
            "emr.ChargeItemDefinition",
            facility=facility,
            title="Test Charge Item Definition",
            description="Test Charge Item Definition",
            slug=f"f-{facility.external_id}-test-charge-item-def",
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
            charge_item_definition=charge_item_definition
            or self.charge_item_definition,
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
            total_net=Decimal(4500),
            total_gross=Decimal(4500),
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
        location=None,
    ):
        return {
            "account": account or str(self.account.external_id),
            "target_invoice": target_invoice or str(self.invoice.external_id),
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
            "location": location or str(self.facility_location.external_id),
        }

    def create_payment_reconciliation(self, facility=None, **kwargs):
        data = self.generate_payment_reconciliation_data(**kwargs)
        payment_reconciliation = baker.make(
            "emr.PaymentReconciliation", facility=facility or self.facility, **data
        )
        from care.emr.resources.account.sync_items import rebalance_account_task

        rebalance_account_task(payment_reconciliation.account_id)
        return payment_reconciliation

    # Test cases for create payment reconciliation

    def test_create_payment_reconciliation_as_super_user(self):
        """
        Test creating a payment reconciliation as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(float(get_response.data["amount"]), 4500.00)
        self.assertEqual(float(get_response.data["tendered_amount"]), 4500.00)
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)

    def test_create_payment_reconciliation_as_user_with_permission(self):
        """
        Test creating a payment reconciliation as a user with permission
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(float(get_response.data["amount"]), 4500.00)
        self.assertEqual(float(get_response.data["tendered_amount"]), 4500.00)
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)

    def test_create_payment_reconciliation_as_user_without_permission(self):
        """
        Test creating a payment reconciliation as a user without permission
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write payment reconciliation", response.data["detail"])

    def test_create_payment_reconciliation_with_invalid_account(self):
        """
        Test creating a payment reconciliation with an account not associated with the facility
        """
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        other_account = self.create_account(facility=other_facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(
                account=str(other_account.external_id)
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Account is not associated with the facility", status_code=400
        )

    def test_create_payment_reconciliation_with_invalid_invoice(self):
        """
        Test creating a payment reconciliation with an invoice not associated with the facility
        """
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        other_invoice = self.create_invoice(facility=other_facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(
                target_invoice=other_invoice.external_id
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Invoice is not associated with the facility", status_code=400
        )

    def test_create_payment_reconciliation_with_returned_amount_greater_than_tendered_amount(
        self,
    ):
        """
        Test creating a payment reconciliation with returned amount greater than tendered amount
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(
                tendered_amount=4000.00, returned_amount=4500.00
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Returned amount cannot be greater than tendered amount",
            str(response.data),
        )

    def test_create_payment_reconciliation_with_credit_note(self):
        """
        Test creating a payment reconciliation with credit note
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_payment_reconciliation_data(
            is_credit_note=True, amount=5000.00, tendered_amount=5000.00
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(float(get_response.data["amount"]), 5000.00)
        self.assertEqual(float(get_response.data["tendered_amount"]), 5000.00)
        self.assertTrue(get_response.data["is_credit_note"], "true")
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_gross), 4500.00)
        self.assertEqual(float(self.account.total_paid), -5000.00)
        self.assertEqual(float(self.account.total_balance), 9500.00)

    def test_create_payment_reconciliation_without_location(self):
        """
        Test creating a payment reconciliation without location
        """
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(
            permissions=[
                PaymentReconciliationPermissions.can_read_payment_reconciliation.name,
                PaymentReconciliationPermissions.can_write_payment_reconciliation.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        data = self.generate_payment_reconciliation_data()
        data.pop("location")
        response = self.client.post(
            self.base_url,
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertIsNone(get_response.data["location"])
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)

    def test_create_payment_reconciliation_without_location_permission(self):
        """
        Test creating a payment reconciliation without location permission
        """
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(
            permissions=[
                PaymentReconciliationPermissions.can_read_payment_reconciliation.name,
                PaymentReconciliationPermissions.can_write_payment_reconciliation.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(
                location=str(self.facility_location.external_id)
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to given location", str(response.data)
        )

    def test_create_payment_reconciliation_with_invalid_location(self):
        """
        Test creating a payment reconciliation with an location not associated with the facility
        """
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        other_location = self.create_facility_location(facility=other_facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.base_url,
            data=self.generate_payment_reconciliation_data(
                location=str(other_location.external_id)
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Location is not associated with the facility", status_code=400
        )

    def test_create_payment_reconciliation_without_invoice(self):
        """
        Test creating a payment reconciliation without an invoice
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_payment_reconciliation_data()
        data.pop("target_invoice")
        response = self.client.post(
            self.base_url,
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    # Test cases for update payment reconciliation

    def test_update_payment_reconciliation_as_super_user(self):
        """
        Test updating a payment reconciliation as a superuser
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(payment_reconciliation.external_id),
            data=self.generate_payment_reconciliation_data(
                status=PaymentReconciliationStatusOptions.draft.value,
                note="Updated Note",
                outcome=PaymentReconciliationOutcomeOptions.error.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["status"], "draft")
        self.assertEqual(get_response.data["note"], "Updated Note")
        self.assertEqual(get_response.data["outcome"], "error")

        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 0.00)
        self.assertEqual(float(self.account.total_balance), 4500.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

    def test_update_payment_reconciliation_as_user_with_permission(self):
        """
        Test updating a payment reconciliation as a user with permission
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.put(
            self.get_detail_url(payment_reconciliation.external_id),
            data=self.generate_payment_reconciliation_data(
                status=PaymentReconciliationStatusOptions.draft.value,
                note="Updated Note",
                outcome=PaymentReconciliationOutcomeOptions.error.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["status"], "draft")
        self.assertEqual(get_response.data["note"], "Updated Note")
        self.assertEqual(get_response.data["outcome"], "error")

        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 0.00)
        self.assertEqual(float(self.account.total_balance), 4500.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

    def test_update_payment_reconciliation_as_user_without_permission(self):
        """
        Test updating a payment reconciliation as a user without write permission
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.create_role_with_permissions(
                permissions=[
                    PaymentReconciliationPermissions.can_read_payment_reconciliation.name,
                ]
            ),
        )
        response = self.client.put(
            self.get_detail_url(payment_reconciliation.external_id),
            data=self.generate_payment_reconciliation_data(
                status=PaymentReconciliationStatusOptions.draft.value,
                note="Updated Note",
                outcome=PaymentReconciliationOutcomeOptions.error.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot update payment reconciliation", response.data["detail"])

    def test_update_payment_reconciliation_with_invalid_facility(self):
        """
        Test updating a payment reconciliation with an invalid facility
        """
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=other_facility,
            target_invoice=self.invoice,
            account=self.account,
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(
                payment_reconciliation.external_id,
                facility_external_id=self.facility.external_id,
            ),
            data=self.generate_payment_reconciliation_data(
                status=PaymentReconciliationStatusOptions.draft.value,
                note="Updated Note",
                outcome=PaymentReconciliationOutcomeOptions.error.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            "No PaymentReconciliation matches the given query",
            status_code=404,
        )

    def test_update_payment_reconciliation_status_to_cancelled(self):
        """
        Test updating a payment reconciliation status to cancelled
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(payment_reconciliation.external_id),
            data=self.generate_payment_reconciliation_data(
                status=PaymentReconciliationStatusOptions.cancelled.value,
                note="Updated Note",
                outcome=PaymentReconciliationOutcomeOptions.error.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Cannot update payment reconciliation, use the cancel endpoint instead",
            str(response.data),
        )

    # Test cases for retrieve payment reconciliation

    def test_retrieve_payment_reconciliation_as_super_user(self):
        """
        Test retrieving a payment reconciliation as a superuser
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(payment_reconciliation.external_id))

    def test_retrieve_payment_reconciliation_as_user_with_permission(self):
        """
        Test retrieving a payment reconciliation as a user with permission
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(payment_reconciliation.external_id))

    def test_retrieve_payment_reconciliation_as_user_without_permission(self):
        """
        Test retrieving a payment reconciliation as a user without permission
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read payment reconciliation", response.data["detail"])

    def test_retrieve_payment_reconciliation_with_invalid_facility(self):
        """
        Test retrieving a payment reconciliation with an invalid facility
        """
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=other_facility,
            target_invoice=self.invoice,
            account=self.account,
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(
                payment_reconciliation.external_id,
                facility_external_id=self.facility.external_id,
            )
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            "No PaymentReconciliation matches the given query",
            status_code=404,
        )

    # Test cases for list payment reconciliation

    def test_list_payment_reconciliation_as_super_user(self):
        """
        Test listing payment reconciliations as a superuser
        """
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        payment_reconciliation_2 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        ids = [result["id"] for result in response.data["results"]]
        self.assertIn(str(payment_reconciliation_1.external_id), ids)
        self.assertIn(str(payment_reconciliation_2.external_id), ids)

    def test_list_payment_reconciliation_as_user_with_permission(self):
        """
        Test listing payment reconciliations as a user with permission
        """
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        payment_reconciliation_2 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        ids = [result["id"] for result in response.data["results"]]
        self.assertIn(str(payment_reconciliation_1.external_id), ids)
        self.assertIn(str(payment_reconciliation_2.external_id), ids)

    def test_list_payment_reconciliation_as_user_without_permission(self):
        """
        Test listing payment reconciliations as a user without permission
        """
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read payment reconciliation", response.data["detail"])

    def test_list_payment_reconciliation_with_invalid_facility(self):
        """
        Test listing payment reconciliations with an invalid facility
        """
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=other_facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=other_facility,
            target_invoice=self.invoice,
            account=self.account,
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_base_url(facility_external_id=self.facility.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_filter_payment_reconciliation_by_account(self):
        """
        Test filtering payment reconciliations by account
        """
        other_account = self.create_account(facility=self.facility)
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=other_account,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url, {"account": str(self.account.external_id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(payment_reconciliation_1.external_id)
        )

    def test_filter_payment_reconciliation_by_status(self):
        """
        Test filtering payment reconciliations by status
        """
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
            status=PaymentReconciliationStatusOptions.active.value,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
            status=PaymentReconciliationStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url, {"status": PaymentReconciliationStatusOptions.active.value}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(payment_reconciliation_1.external_id)
        )

    def test_filter_payment_reconciliation_by_target_invoice(self):
        """
        Test filtering payment reconciliations by target invoice
        """
        other_invoice = self.create_invoice(
            facility=self.facility, account=self.account, patient=self.patient
        )
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=other_invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url, {"target_invoice": str(self.invoice.external_id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(payment_reconciliation_1.external_id)
        )

    def test_filter_payment_reconciliation_by_reconciliation_type(self):
        """
        Test filtering payment reconciliations by reconciliation type
        """
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
            reconciliation_type=PaymentReconciliationTypeOptions.payment.value,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
            reconciliation_type=PaymentReconciliationTypeOptions.adjustment.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {"reconciliation_type": PaymentReconciliationTypeOptions.payment.value},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(payment_reconciliation_1.external_id)
        )

    def test_filter_payment_reconciliation_by_is_credit_note(self):
        """
        Test filtering payment reconciliations by is_credit_note
        """
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
            is_credit_note=True,
        )
        self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url, {"is_credit_note": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(payment_reconciliation_1.external_id)
        )

    def test_filter_payment_reconciliation_by_location(self):
        """
        Test filtering payment reconciliations by location
        """
        other_location = self.create_facility_location(facility=self.facility)
        payment_reconciliation_1 = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.create_payment_reconciliation(
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
            location=other_location,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url, {"location": str(self.facility_location.external_id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(payment_reconciliation_1.external_id)
        )

    # Test cases for cancel payment reconciliation

    def test_cancel_payment_reconciliation_as_super_user(self):
        """
        Test cancelling a payment reconciliation as a superuser
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.get_cancel_url(
                self.facility.external_id,
                payment_reconciliation.external_id,
            ),
            {"reason": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["id"], str(payment_reconciliation.external_id)
        )
        self.assertEqual(get_response.data["status"], "cancelled")
        self.account.refresh_from_db()

        self.assertEqual(float(self.account.total_paid), 0.00)
        self.assertEqual(float(self.account.total_balance), 4500.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

    def test_cancel_payment_reconciliation_as_user_with_permission(self):
        """
        Test cancelling a payment reconciliation as a user with permission
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.get_cancel_url(
                self.facility.external_id,
                payment_reconciliation.external_id,
            ),
            {"reason": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(payment_reconciliation.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["id"], str(payment_reconciliation.external_id)
        )
        self.assertEqual(get_response.data["status"], "cancelled")
        self.account.refresh_from_db()

        self.assertEqual(float(self.account.total_paid), 0.00)
        self.assertEqual(float(self.account.total_balance), 4500.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

    def test_cancel_payment_reconciliation_as_user_without_permission(self):
        """
        Test cancelling a payment reconciliation as a user without permission
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.create_role_with_permissions(
                permissions=[
                    PaymentReconciliationPermissions.can_read_payment_reconciliation.name,
                ]
            ),
        )
        response = self.client.post(
            self.get_cancel_url(
                self.facility.external_id,
                payment_reconciliation.external_id,
            ),
            {"reason": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cancel_payment_reconciliation_with_invalid_reason(self):
        """
        Test cancelling a payment reconciliation with an invalid reason
        """
        payment_reconciliation = self.create_payment_reconciliation(
            location=self.facility_location,
            facility=self.facility,
            target_invoice=self.invoice,
            account=self.account,
        )
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.total_paid), 4500.00)
        self.assertEqual(float(self.account.total_balance), 0.00)
        self.assertEqual(float(self.account.total_gross), 4500.00)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.get_cancel_url(
                self.facility.external_id,
                payment_reconciliation.external_id,
            ),
            {"reason": "draft"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid reason", response.data["errors"][0]["msg"])
