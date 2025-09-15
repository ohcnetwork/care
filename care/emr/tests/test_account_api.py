from datetime import datetime

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
        self.patient = self.create_patient()
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

    def get_rebalance_url(self, facility_external_id, external_id):
        return reverse("account-rebalance", args=[facility_external_id, external_id])

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
