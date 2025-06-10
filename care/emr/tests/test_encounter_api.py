from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status

from care.emr.models.location import FacilityLocation, FacilityLocationEncounter
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class EncounterAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("encounter-list")

    def _get_details_url(self):
        return reverse(
            "encounter-detail", kwargs={"external_id": self.encounter.external_id}
        )

    def get_list_view_permission(self):
        permissions = [
            EncounterPermissions.can_list_encounter.name,
            # EncounterPermissions.can_read_encounter.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )

    #  TESTS FOR LIST FILTERS

    def test_filter_by_facility(self):
        self.get_list_view_permission()
        response = self.client.get(self.url, {"facility": self.facility.external_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_status(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {"status": self.encounter.status, "facility": self.facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_patient_name(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url, {"name": self.patient.name, "facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_patient_phone(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "phone_number": self.patient.phone_number,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_location(self):
        location = baker.make(
            FacilityLocation,
            facility=self.facility,
            status="ACTIVE",
            operational_status="ACTIVE",
            name="Test Location",
            description="Test Description",
            mode="INSTANCE",
            form="AREA",
        )

        baker.make(
            FacilityLocationEncounter,
            location=location,
            encounter=self.encounter,
            status="ACTIVE",
            start_datetime=timezone.now(),
        )
        location.current_encounter = self.encounter
        location.save()
        self.encounter.current_location = location
        self.encounter.save()

        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "location": str(location.external_id),
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filters_by_live(self):
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            status="completed",
        )
        self.get_list_view_permission()
        response = self.client.get(
            self.url, {"live": True, "facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(encounter.external_id))

        response = self.client.get(
            self.url, {"live": False, "facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_external_identifier(self):
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            external_identifier="12345",
        )
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "external_identifier": encounter.external_identifier,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(encounter.external_id))

    def test_filter_encounter_class(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "encounter_class": self.encounter.encounter_class,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_priority(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "priority": self.encounter.priority,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))
