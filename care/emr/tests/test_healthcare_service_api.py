from django.urls import reverse
from model_bakery import baker

from care.emr.resources.healthcare_service.spec import HealthcareServiceInternalType
from care.security.permissions.healthcare_service import HealthcareServicePermissions
from care.utils.tests.base import CareAPITestBase


class HealthcareServiceAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.super_user = self.create_super_user()
        self.facility = self.create_facility(name="Test Facility", user=self.super_user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.facility_location = self.create_facility_location(self.facility)
        self.base_url = reverse(
            "healthcare_service-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        self.healthcare_service_data = {
            "name": "Test Healthcare Service",
            "service_type": {"code": "test_code", "display": "Test Code"},
            "internal_type": HealthcareServiceInternalType.pharmacy,
            "locations": [self.facility_location.external_id],
            "extra_details": "Some extra details about the service.",
        }
        self.update_data = {
            "name": "Updated Healthcare Service",
            "service_type": {"code": "updated_code", "display": "Updated Code"},
            "internal_type": HealthcareServiceInternalType.lab,
            "locations": [self.facility_location.external_id],
            "extra_details": "Updated extra details about the service.",
        }
        self.role = self.create_role_with_permissions(
            permissions=[
                HealthcareServicePermissions.can_read_healthcare_service.name,
                HealthcareServicePermissions.can_write_healthcare_service.name,
            ]
        )

    def get_detail_url(self, external_id):
        return reverse(
            "healthcare_service-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def create_facility_location(self, facility):
        return baker.make(
            "emr.FacilityLocation",
            facility=facility,
            name="Test Location",
        )

    def create_healthcare_service(self, facility, **kwargs):
        from care.emr.models import HealthcareService

        return baker.make(
            HealthcareService,
            facility=facility,
            **kwargs,
        )

    # Test for creating a healthcare service

    def test_create_healthcare_service_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            self.base_url, self.healthcare_service_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_healthcare_service_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.healthcare_service_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_healthcare_service_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.healthcare_service_data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Healthcare Service", status_code=403
        )

    # Test for retrieving a healthcare service

    def test_retrieve_healthcare_service_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        healthcare_service = self.create_healthcare_service(
            facility=self.facility, name="Test Healthcare Service"
        )
        response = self.client.get(self.get_detail_url(healthcare_service.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(healthcare_service.external_id))

    def test_retrieve_healthcare_service_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        healthcare_service = self.create_healthcare_service(
            facility=self.facility, name="Test Healthcare Service"
        )
        response = self.client.get(self.get_detail_url(healthcare_service.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(healthcare_service.external_id))

    def test_retrieve_healthcare_service_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        healthcare_service = self.create_healthcare_service(
            facility=self.facility, name="Test Healthcare Service"
        )
        response = self.client.get(self.get_detail_url(healthcare_service.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Healthcare Service", status_code=403
        )

        # Test for updating a healthcare service

    def test_update_healthcare_service_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        healthcare_service = self.create_healthcare_service(
            facility=self.facility, name="Test Healthcare Service"
        )
        response = self.client.put(
            self.get_detail_url(healthcare_service.external_id),
            self.update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(healthcare_service.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], self.update_data["name"])

    def test_update_healthcare_service_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        healthcare_service = self.create_healthcare_service(
            facility=self.facility, name="Test Healthcare Service"
        )
        response = self.client.put(
            self.get_detail_url(healthcare_service.external_id),
            self.update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(healthcare_service.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], self.update_data["name"])

    def test_update_healthcare_service_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        healthcare_service = self.create_healthcare_service(
            facility=self.facility, name="Test Healthcare Service"
        )
        response = self.client.put(
            self.get_detail_url(healthcare_service.external_id),
            self.update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Healthcare Service", status_code=403
        )
