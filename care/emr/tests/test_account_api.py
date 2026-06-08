from datetime import datetime
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.security.permissions.account import AccountPermissions
from care.utils.tests.base import CareAPITestBase


class AccountAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="testsuperuser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.patient = self.create_patient(name="Test Patient")
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Facility Org", org_type="root"
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                AccountPermissions.can_create_account.name,
                AccountPermissions.can_update_account.name,
                AccountPermissions.can_read_account.name,
            ]
        )

    def get_base_url(self, facility_external_id):
        return reverse("account-list", args=[facility_external_id])

    def get_detail_url(self, facility_external_id, external_id):
        return reverse("account-detail", args=[facility_external_id, external_id])

    def generate_account_data(self, **kwargs):
        default_start = str(timezone.make_aware(datetime(2023, 1, 1)))
        default_end = str(timezone.make_aware(datetime(2023, 12, 31)))

        return {
            "status": kwargs.get("status", AccountStatusOptions.active),
            "billing_status": kwargs.get(
                "billing_status", AccountBillingStatusOptions.open
            ),
            "name": kwargs.get("name", "Test Account"),
            "service_period": {"start": default_start, "end": default_end},
            "description": kwargs.get("description", "Test Description"),
            "patient": kwargs.get("patient", self.patient),
            **kwargs,
        }

    def get_account(self, facility, **kwargs):
        data = self.generate_account_data(**kwargs)
        return baker.make("emr.Account", facility=facility, **data)

    # Test cases for create account

    def test_create_account_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_account_data(patient=self.patient.external_id)
        response = self.client.post(
            self.get_base_url(self.facility.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"])
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(get_response.data["patient"]["id"], str(data["patient"]))

    def test_create_account_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_account_data(patient=self.patient.external_id)
        response = self.client.post(
            self.get_base_url(self.facility.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(str(self.facility.external_id), response.data["id"])
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(get_response.data["patient"]["id"], str(data["patient"]))

    def test_create_account_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self.generate_account_data(patient=self.patient.external_id)
        response = self.client.post(
            self.get_base_url(self.facility.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You are not authorized to create accounts", response.data["detail"]
        )

    def test_create_account_with_existing_active_account_for_that_patient(self):
        self.client.force_authenticate(user=self.superuser)
        self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        data = self.generate_account_data(patient=self.patient.external_id)
        response = self.client.post(
            self.get_base_url(self.facility.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Active account already exists for this patient", str(response.data)
        )

    # Test cases for update account

    def test_update_account_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.inactive,
            description="Updated Description",
            billing_status=AccountBillingStatusOptions.closed_completed,
            patient=self.patient.external_id,
        )
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, account.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(get_response.data["patient"]["id"], str(data["patient"]))

    def test_update_account_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.inactive,
            description="Updated Description",
            billing_status=AccountBillingStatusOptions.closed_completed,
            patient=self.patient.external_id,
        )
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, account.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(get_response.data["patient"]["id"], str(data["patient"]))

    def test_update_account_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(
            permissions=[
                AccountPermissions.can_read_account.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.inactive,
            description="Updated Description",
            billing_status=AccountBillingStatusOptions.closed_completed,
            patient=self.patient.external_id,
        )
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You are not authorized to update accounts", response.data["detail"]
        )

    def test_update_account_with_existing_active_account_for_that_patient(self):
        self.client.force_authenticate(user=self.superuser)
        self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        account2 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
            patient=self.patient.external_id,
        )
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account2.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Active account already exists for this patient", str(response.data)
        )

    def test_update_new_account_if_no_active_account_exists_for_that_patient(self):
        self.client.force_authenticate(user=self.superuser)
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
            patient=self.patient.external_id,
        )
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, account.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(get_response.data["patient"]["id"], str(data["patient"]))

    def test_update_with_primary_encounter_different_facility(self):
        self.client.force_authenticate(user=self.superuser)
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        other_facility_org = self.create_facility_organization(
            facility=other_facility, name="Other Facility Org", org_type="root"
        )
        encounter = self.create_encounter(
            patient=self.patient,
            facility=other_facility,
            status="active",
            organization=other_facility_org,
        )
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
            patient=self.patient.external_id,
        )
        data["primary_encounter"] = str(encounter.external_id)
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Primary encounter must belong to the same facility", str(response.data)
        )

    def test_update_with_primary_encounter_different_patient(self):
        self.client.force_authenticate(user=self.superuser)
        other_patient = self.create_patient(name="Other Patient")
        encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
            patient=self.patient.external_id,
        )
        data["primary_encounter"] = str(encounter.external_id)
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Primary encounter must belong to the same patient", str(response.data)
        )

    def test_update_with_primary_encounter_already_linked_to_another_active_account(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.closed_completed,
            primary_encounter=encounter,
        )
        account2 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        data = self.generate_account_data(
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
            patient=self.patient.external_id,
            primary_encounter=str(encounter.external_id),
        )
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, account2.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Encounter is already associated with an account", str(response.data)
        )

    def test_default_account_action(self):
        self.client.force_authenticate(user=self.superuser)
        self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        url = reverse(
            "account-default-account",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(
            url,
            {
                "patient": str(self.patient.external_id),
                "facility": str(self.facility.external_id),
                "encounter": str(encounter.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_default_account_no_account_found(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, "non-existent-id")
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("No Account matches the given query", str(response.data))

    def test_default_account_encounter_not_associated_with_patient(self):
        self.client.force_authenticate(user=self.superuser)
        other_patient = self.create_patient(name="Other Patient")
        encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        url = reverse(
            "account-default-account",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(
            url,
            {
                "patient": str(self.patient.external_id),
                "facility": str(self.facility.external_id),
                "encounter": str(encounter.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "Encounter is not associated with the patient", str(response.data)
        )

    def test_default_account_encounter_not_associated_with_facility(self):
        self.client.force_authenticate(user=self.superuser)
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        encounter = self.create_encounter(
            patient=self.patient,
            facility=other_facility,
            status="active",
            organization=self.facility_organization,
        )
        url = reverse(
            "account-default-account",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(
            url,
            {
                "patient": str(self.patient.external_id),
                "facility": str(self.facility.external_id),
                "encounter": str(encounter.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "Encounter is not associated with the facility", str(response.data)
        )

    def test_default_account_with_primary_encounter_exists(self):
        self.client.force_authenticate(user=self.superuser)
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
            primary_encounter=encounter,
        )
        url = reverse(
            "account-default-account",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(
            url,
            {
                "patient": str(self.patient.external_id),
                "facility": str(self.facility.external_id),
                "encounter": str(encounter.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(account.external_id))

    def test_default_account_for_encounter_without_account(self):
        self.client.force_authenticate(user=self.superuser)
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )
        url = reverse(
            "account-default-account",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(
            url,
            {
                "patient": str(self.patient.external_id),
                "facility": str(self.facility.external_id),
                "encounter": str(encounter.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No account found", str(response.data["errors"][0]["msg"]))

    # Test cases for retrieve account

    def test_retrieve_account_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, account.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(account.external_id))
        self.assertEqual(
            response.data["patient"]["id"], str(account.patient.external_id)
        )

    def test_retrieve_account_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, account.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(account.external_id))
        self.assertEqual(
            response.data["patient"]["id"], str(account.patient.external_id)
        )

    def test_retrieve_account_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        account = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, account.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You are not authorized to read accounts", response.data["detail"]
        )

    # Test cases for listing account

    def test_list_account_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        account1 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        account2 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        response = self.client.get(
            self.get_base_url(self.facility.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(account1.external_id), returned_ids)
        self.assertIn(str(account2.external_id), returned_ids)

    def test_list_account_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        account1 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        account2 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        response = self.client.get(
            self.get_base_url(self.facility.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(account1.external_id), returned_ids)
        self.assertIn(str(account2.external_id), returned_ids)

    def test_list_account_with_status_filter(self):
        self.client.force_authenticate(user=self.superuser)
        account1 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        response = self.client.get(
            self.get_base_url(self.facility.external_id),
            {"status": AccountStatusOptions.active},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(account1.external_id))

    def test_list_account_with_name_filter(self):
        self.client.force_authenticate(user=self.superuser)
        account1 = self.get_account(
            self.facility,
            patient=self.patient,
            name="Special Account Name",
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        self.get_account(
            self.facility,
            patient=self.patient,
            name="Another Name",
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        response = self.client.get(
            self.get_base_url(self.facility.external_id), {"name": "Special"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(account1.external_id))

    def test_list_account_with_billing_status_filter(self):
        self.client.force_authenticate(user=self.superuser)
        account1 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.inactive,
            billing_status=AccountBillingStatusOptions.closed_completed,
        )
        response = self.client.get(
            self.get_base_url(self.facility.external_id),
            {"billing_status": AccountBillingStatusOptions.open},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(account1.external_id))

    def test_list_account_with_patient_filter(self):
        self.client.force_authenticate(user=self.superuser)
        patient2 = self.create_patient(name="Another Patient")
        account1 = self.get_account(
            self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        self.get_account(
            self.facility,
            patient=patient2,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        response = self.client.get(
            self.get_base_url(self.facility.external_id),
            {"patient": str(self.patient.external_id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(account1.external_id))


class RebalanceAccountTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="testsuperuser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.patient = self.create_patient(name="Test Patient")
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Facility Org", org_type="root"
        )

        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            status="active",
            organization=self.facility_organization,
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                AccountPermissions.can_create_account.name,
                AccountPermissions.can_update_account.name,
                AccountPermissions.can_read_account.name,
            ]
        )
        self.account = baker.make(
            "emr.Account",
            facility=self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active,
            billing_status=AccountBillingStatusOptions.open,
        )
        self.category = baker.make(
            "emr.ResourceCategory",
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-test-category",
            title="Test Category",
            description="Test Charge Item Category",
        )
        self.charge_item_definition = baker.make(
            "emr.ChargeItemDefinition",
            facility=self.facility,
            title="Test Charge Item Definition",
            description="Test Charge Item Definition",
            slug=f"f-{self.facility.external_id}-test-charge-item-def",
            price_components=[{"amount": 500, "monetary_component_type": "base"}],
            category=self.category,
        )
        self.charge_item = baker.make(
            "emr.ChargeItem",
            facility=self.facility,
            encounter=self.encounter,
            charge_item_definition=self.charge_item_definition,
            account=self.account,
            title="Test Charge Item",
            status="billed",
            code=None,
            quantity="1.00",
            unit_price_components=[{"amount": 500, "monetary_component_type": "base"}],
            note=None,
            override_reason=None,
            total_price_components=[{"amount": 500, "monetary_component_type": "base"}],
            total_price="500.00",
            service_resource="service_request",
            service_resource_id=str(self.encounter.external_id),
        )
        self.invoice = baker.make(
            "emr.Invoice",
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            status="issued",
            total_net=500,
            total_gross=500,
            issue_date=timezone.now(),
        )

    def create_payment_reconciliation(
        self,
        account,
        invoice,
        amount=None,
        tendered_amount=None,
        returned_amount=None,
        is_credit_note=False,
    ):
        return baker.make(
            "emr.PaymentReconciliation",
            facility=self.facility,
            target_invoice=invoice,
            account=account,
            status="active",
            outcome="complete",
            amount=amount or 300,
            tendered_amount=tendered_amount or 300,
            returned_amount=returned_amount or 0,
            is_credit_note=is_credit_note,
            method="cash",
            reconciliation_type="payment",
            kind="deposit",
            issuer_type="patient",
        )

    def get_detail_url(self, facility_external_id, external_id):
        return reverse("account-detail", args=[facility_external_id, external_id])

    def get_rebalance_url(self, facility_external_id, external_id):
        return reverse("account-rebalance", args=[facility_external_id, external_id])

    def test_rebalance_account_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        initial_balance = self.account.total_balance
        initial_gross = self.account.total_gross
        initial_paid = self.account.total_paid
        self.assertEqual(initial_balance, Decimal("0.00"))
        self.assertEqual(initial_gross, Decimal("0.00"))
        self.assertEqual(initial_paid, Decimal("0.00"))
        self.create_payment_reconciliation(self.account, self.invoice)

        response = self.client.post(
            self.get_rebalance_url(self.facility.external_id, self.account.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()

        self.assertEqual(self.account.total_gross, Decimal("500.00"))
        self.assertEqual(self.account.total_paid, Decimal("300.00"))
        self.assertEqual(self.account.total_balance, Decimal("200.00"))
        self.assertIsNotNone(self.account.calculated_at)

    def test_rebalance_account_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        initial_balance = self.account.total_balance
        initial_gross = self.account.total_gross
        initial_paid = self.account.total_paid
        self.assertEqual(initial_balance, Decimal("0.00"))
        self.assertEqual(initial_gross, Decimal("0.00"))
        self.assertEqual(initial_paid, Decimal("0.00"))
        self.create_payment_reconciliation(self.account, self.invoice)

        response = self.client.post(
            self.get_rebalance_url(self.facility.external_id, self.account.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()

        self.assertEqual(self.account.total_gross, Decimal("500.00"))
        self.assertEqual(self.account.total_paid, Decimal("300.00"))
        self.assertEqual(self.account.total_balance, Decimal("200.00"))
        self.assertIsNotNone(self.account.calculated_at)

    def test_rebalance_account_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(
            permissions=[
                AccountPermissions.can_read_account.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        initial_balance = self.account.total_balance
        initial_gross = self.account.total_gross
        initial_paid = self.account.total_paid
        self.assertEqual(initial_balance, Decimal("0.00"))
        self.assertEqual(initial_gross, Decimal("0.00"))
        self.assertEqual(initial_paid, Decimal("0.00"))
        self.create_payment_reconciliation(self.account, self.invoice)

        response = self.client.post(
            self.get_rebalance_url(self.facility.external_id, self.account.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You are not authorized to update accounts", response.data["detail"]
        )

    def test_rebalance_account_with_credit_note(self):
        self.client.force_authenticate(user=self.superuser)
        initial_balance = self.account.total_balance
        initial_gross = self.account.total_gross
        initial_paid = self.account.total_paid
        self.assertEqual(initial_balance, Decimal("0.00"))
        self.assertEqual(initial_gross, Decimal("0.00"))
        self.assertEqual(initial_paid, Decimal("0.00"))
        self.create_payment_reconciliation(self.account, self.invoice)
        self.create_payment_reconciliation(
            self.account, self.invoice, amount=200, is_credit_note=True
        )

        response = self.client.post(
            self.get_rebalance_url(self.facility.external_id, self.account.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()

        self.assertEqual(self.account.total_gross, Decimal("500.00"))
        self.assertEqual(self.account.total_paid, Decimal("100.00"))
        self.assertEqual(self.account.total_balance, Decimal("400.00"))
        self.assertIsNotNone(self.account.calculated_at)
