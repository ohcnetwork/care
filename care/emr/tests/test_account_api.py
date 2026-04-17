from django.urls import reverse
from rest_framework import status

from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.utils.tests.base import CareAPITestBase


class TestAccountViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.superuser)
        self.base_url = reverse(
            "account-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, account_id):
        return reverse(
            "account-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": account_id,
            },
        )

    def _get_account_data(self, **overrides):
        data = {
            "status": AccountStatusOptions.active.value,
            "billing_status": AccountBillingStatusOptions.open.value,
            "name": "Test Account",
            "service_period": {
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-12-31T23:59:59Z",
            },
            "patient": str(self.patient.external_id),
        }
        data.update(overrides)
        return data

    def test_create_account(self):
        data = self._get_account_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Account")

    def test_list_accounts(self):
        self.client.post(self.base_url, self._get_account_data(), format="json")
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_retrieve_account(self):
        create_res = self.client.post(
            self.base_url, self._get_account_data(), format="json"
        )
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        url = self._get_detail_url(create_res.data["id"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], create_res.data["id"])

    def test_update_account(self):
        create_res = self.client.post(
            self.base_url, self._get_account_data(), format="json"
        )
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        url = self._get_detail_url(create_res.data["id"])
        update_data = self._get_account_data(
            name="Updated Account",
            status=AccountStatusOptions.inactive.value,
        )
        del update_data["patient"]
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Account")
        self.assertEqual(response.data["status"], AccountStatusOptions.inactive.value)

    def test_duplicate_active_open_account_for_patient(self):
        data = self._get_account_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response2 = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Active account already exists", str(response2.data))

    def test_allow_second_account_when_first_inactive(self):
        data = self._get_account_data(status=AccountStatusOptions.inactive.value)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data2 = self._get_account_data()
        response2 = self.client.post(self.base_url, data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_filter_by_status(self):
        self.client.post(self.base_url, self._get_account_data(), format="json")
        patient2 = self.create_patient()
        self.client.post(
            self.base_url,
            self._get_account_data(
                patient=str(patient2.external_id),
                status=AccountStatusOptions.inactive.value,
            ),
            format="json",
        )
        response = self.client.get(
            self.base_url, {"status": AccountStatusOptions.active.value}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertEqual(r["status"], AccountStatusOptions.active.value)

    def test_filter_by_patient(self):
        self.client.post(self.base_url, self._get_account_data(), format="json")
        patient2 = self.create_patient()
        self.client.post(
            self.base_url,
            self._get_account_data(patient=str(patient2.external_id)),
            format="json",
        )
        response = self.client.get(
            self.base_url, {"patient": str(self.patient.external_id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_filter_by_billing_status(self):
        self.client.post(self.base_url, self._get_account_data(), format="json")
        response = self.client.get(
            self.base_url,
            {"billing_status": AccountBillingStatusOptions.open.value},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertEqual(
                r["billing_status"], AccountBillingStatusOptions.open.value
            )

    def test_update_with_primary_encounter_different_facility(self):
        create_res = self.client.post(
            self.base_url, self._get_account_data(), format="json"
        )
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        other_facility = self.create_facility(user=self.superuser)
        other_org = self.create_facility_organization(facility=other_facility)
        encounter = self.create_encounter(
            patient=self.patient, facility=other_facility, organization=other_org
        )
        url = self._get_detail_url(create_res.data["id"])
        update_data = self._get_account_data(
            primary_encounter=str(encounter.external_id)
        )
        del update_data["patient"]
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            "Primary encounter is not associated with the facility",
            response.data["detail"],
        )

    def test_update_with_primary_encounter_different_patient(self):
        create_res = self.client.post(
            self.base_url, self._get_account_data(), format="json"
        )
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        other_patient = self.create_patient()
        encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        url = self._get_detail_url(create_res.data["id"])
        update_data = self._get_account_data(
            primary_encounter=str(encounter.external_id)
        )
        del update_data["patient"]
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            "Primary encounter is not associated with the patient",
            response.data["detail"],
        )

    def test_default_account_action(self):
        create_res = self.client.post(
            self.base_url, self._get_account_data(), format="json"
        )
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_default_account_no_account_found(self):
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No account found", str(response.data))
