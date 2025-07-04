from django.urls import reverse
from model_bakery import baker

from care.emr.resources.specimen.spec import SpecimenStatusOptions
from care.security.permissions.specimen import SpecimenPermissions
from care.utils.tests.base import CareAPITestBase


class TestSpecimenViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.facility_location = self.create_facility_location()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            current_location=self.facility_location,
        )
        self.service_request = self.create_service_request(
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                SpecimenPermissions.can_read_specimen.name,
                SpecimenPermissions.can_write_specimen.name,
            ]
        )

    def get_detail_url(self, facility_external_id, external_id):
        return reverse(
            "specimen-detail",
            kwargs={
                "facility_external_id": facility_external_id,
                "external_id": external_id,
            },
        )

    def create_specimen(self, **kwargs):
        return baker.make(
            "emr.Specimen",
            facility=self.facility,
            patient=self.patient,
            encounter=self.encounter,
            service_request=self.service_request,
            status=SpecimenStatusOptions.available.value,
            **kwargs,
        )

    def create_facility_location(self):
        from care.emr.models.location import FacilityLocation

        return baker.make(
            FacilityLocation,
            name="Test facility Locations",
            facility=self.facility,
            status="active",
        )

    def test_retrieve_with_read_permission_as_user(self):
        """Test that a user with read_specimen permission can retrieve a specimen"""
        specimen = self.create_specimen(
            created_by=self.user,
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen.external_id))

    def test_retrieve_without_permission_as_user(self):
        """Test that a user without read_specimen permission cannot retrieve a specimen"""
        specimen = self.create_specimen()
        self.client.force_authenticate(user=self.user)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to read this specimen"
        )

    def test_retrieve_with_read_permission_as_superuser(self):
        """Test that a superuser can retrieve a specimen regardless of permissions"""
        specimen = self.create_specimen()
        self.client.force_authenticate(user=self.superuser)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen.external_id))

    def test_retrieve_without_permission_as_superuser(self):
        """Test that a superuser can retrieve a specimen regardless of permissions"""
        specimen = self.create_specimen()
        self.client.force_authenticate(user=self.superuser)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen.external_id))

    def test_update_with_permission_as_user(self):
        """Test that a user with write_specimen permission can update a specimen"""
        specimen = self.create_specimen()
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        data = {
            "status": SpecimenStatusOptions.unavailable.value,
            "note": "Updated specimen note",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], SpecimenStatusOptions.unavailable.value
        )

    def test_update_without_permission(self):
        """Test that a user without write_specimen permission cannot update a specimen"""
        specimen = self.create_specimen()
        self.client.force_authenticate(user=self.user)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        data = {
            "status": SpecimenStatusOptions.unavailable.value,
            "note": "Updated specimen note",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to write this specimen"
        )
