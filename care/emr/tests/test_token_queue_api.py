from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.scheduling.token import (
    TokenQueue,
)
from care.emr.resources.scheduling.token.spec import SchedulableResourceTypeOptions
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenQueueAPITestCase(CareAPITestBase):
    def setUp(self):
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.facility_location = self.create_facility_location(
            facility=self.facility, facility_organization=self.facility_organization
        )
        self.superuser_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.superuser,
        )
        self.patient = self.create_patient()
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
                TokenPermissions.can_write_token.name,
            ],
        )
        self.base_url = reverse(
            "token-queue-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def generate_token_queue_data(self, **kwargs):
        """
        Generate data for creating a TokenQueue instance.

        fields:
        - resource_type: The type of schedulable resource type for the token queue.
        - resource_id: The external ID of the resource for the token queue.

        These fields are required to validate schedulable resource based on the resource type
        """
        data = {
            "name": "Test Token Queue",
            "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            "resource_type": kwargs.get(
                "resource_type", SchedulableResourceTypeOptions.practitioner.value
            ),
            "resource_id": kwargs.get("resource_id", str(self.superuser.external_id)),
        }
        data.update(kwargs)
        return data

    def create_token_queue(self, facility, **kwargs):
        return baker.make(TokenQueue, facility=facility, **kwargs)

    def generate_detail_url(self, facility_external_id, external_id):
        return reverse(
            "token-queue-detail",
            kwargs={
                "facility_external_id": facility_external_id,
                "external_id": external_id,
            },
        )

    def create_facility_location(self, facility, facility_organization, **kwargs):
        from care.emr.models import FacilityLocation, FacilityLocationOrganization

        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def create_healthcare_service(self, facility, **kwargs):
        return baker.make(HealthcareService, facility=facility, **kwargs)

    # Tests for create token queue

    def test_create_token_queue_with_resource_type_be_practitioner_as_superuser(self):
        """
        Test creating a token queue with resource type be practitioner as superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_token_queue_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(get_response.data["date"], data["date"])

    def test_create_token_queue_with_resource_type_be_practitioner_as_user_with_permissions(
        self,
    ):
        """
        Test creating a token queue with resource type be practitioner as a user with the required permissions.
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        data = self.generate_token_queue_data(resource_id=str(self.user.external_id))
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], data["name"])

    def test_create_token_queue_with_resource_type_be_practitioner_as_user_without_write_permissions(
        self,
    ):
        """
        Test creating a token queue with resource type be practitioner as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_token_queue_data(resource_id=str(self.user.external_id))
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_create_token_queue_with_resource_type_be_practitioner_as_user_outside_facility_organization(
        self,
    ):
        """
        Test creating a token queue with resource type be practitioner as a user without being part of facility organization.
        """
        self.client.force_authenticate(user=self.user)
        data = self.generate_token_queue_data(resource_id=str(self.user.external_id))
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Schedule User is not part of the facility", str(response.data))

    def test_create_token_queue_with_resource_type_be_location_as_superuser(self):
        """
        Test creating a token queue with resource type be location as superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.facility_location.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(get_response.data["date"], data["date"])

    def test_create_token_queue_with_resource_type_be_location_as_user_with_permissions(
        self,
    ):
        """
        Test creating a token queue with resource type be location as a user with the required permissions.
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.facility_location.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(get_response.data["date"], data["date"])

    def test_create_token_queue_with_resource_type_be_location_as_user_without_write_permissions(
        self,
    ):
        """
        Test creating a token queue with resource type be location as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.facility_location.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_create_token_queue_with_resource_type_be_location_as_user_outside_facility_organization(
        self,
    ):
        """
        Test creating a token queue with resource type be location as a user without being part of facility organization.
        """
        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility, org_type="root"
        )
        another_facility_location = self.create_facility_location(
            facility=another_facility,
            facility_organization=another_facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_token_queue_data(
            resource_id=str(another_facility_location.external_id),
            resource_type=SchedulableResourceTypeOptions.location.value,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Location is not part of the facility", str(response.data))

    def test_create_token_queue_with_resource_type_be_healthcare_service_as_superuser(
        self,
    ):
        """
        Test creating a token queue with resource type be healthcare service as superuser.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(get_response.data["date"], data["date"])

    def test_create_token_queue_with_resource_type_be_healthcare_service_as_user_with_permissions(
        self,
    ):
        """
        Test creating a token queue with resource type be healthcare service as a user with the required permissions.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(get_response.data["date"], data["date"])

    def test_create_token_queue_with_resource_type_be_healthcare_service_as_user_without_write_permissions(
        self,
    ):
        """
        Test creating a token queue with resource type be healthcare service as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_create_token_queue_with_resource_type_be_healthcare_service_as_user_outside_facility_organization(
        self,
    ):
        """
        Test creating a token queue with resource type be healthcare service as a user without being part of facility organization.
        """
        another_facility = self.create_facility(user=self.superuser)
        healthcare_service = self.create_healthcare_service(facility=another_facility)
        self.client.force_authenticate(user=self.user)
        data = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Healthcare Service is not part of the facility", str(response.data)
        )

    # Tests for update token queue

    def test_update_token_queue_as_superuser(self):
        """
        Test updating a token queue as superuser.
        """
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], update_data["name"])
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_queue.external_id))
        self.assertEqual(get_response.data["name"], update_data["name"])

    def test_update_token_queue_with_resource_type_be_practitioner_as_user_with_permissions(
        self,
    ):
        """
        Test updating a token queue with resource type be practitioner as a user with the required permissions.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], update_data["name"])
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_queue.external_id))
        self.assertEqual(get_response.data["name"], update_data["name"])

    def test_update_token_queue_with_resource_type_be_practitioner_as_user_without_write_permissions(
        self,
    ):
        """
        Test updating a token queue with resource type be practitioner as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    def test_update_token_queue_with_resource_type_be_practitioner_as_user_outside_facility_organization(
        self,
    ):
        """
        Test updating a token queue with resource type be practitioner as a user outside the facility organization.
        But the user is a part of another facility organization with write permissions.

        """
        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility, org_type="root"
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=another_facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    def test_update_token_queue_with_resource_type_be_healthcare_as_superuser(self):
        """
        Test updating a token queue with resource type be healthcare service as superuser.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        healthcare_service_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=healthcare_service,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=healthcare_service_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], update_data["name"])
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_queue.external_id))
        self.assertEqual(get_response.data["name"], update_data["name"])

    def test_update_token_queue_with_resource_type_be_healthcare_service_as_user_with_permissions(
        self,
    ):
        """
        Test updating a token queue with resource type be healthcare_service as a user with the required permissions.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        healthcare_service_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=healthcare_service,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=healthcare_service_resource,
            is_primary=True,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertIn("Updated Token Queue", str(get_response.data))

    def test_update_token_queue_with_resource_type_be_healthcare_service_as_user_without_write_permissions(
        self,
    ):
        """
        Test updating a token queue with resource type be healthcare_service as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        healthcare_service_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=healthcare_service,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=healthcare_service_resource,
            is_primary=True,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    def test_update_token_queue_with_resource_type_be_location_as_superuser(self):
        """
        Test updating a token queue with resource type be location as superuser.
        """
        location_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.facility_location,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=location_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], update_data["name"])
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_queue.external_id))
        self.assertEqual(get_response.data["name"], update_data["name"])

    def test_update_token_queue_with_resource_type_be_location_as_user_with_permissions(
        self,
    ):
        """
        Test updating a token queue with resource type be location as a user with the required permissions.
        """
        location_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.facility_location,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=location_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_queue.external_id))
        self.assertEqual(get_response.data["name"], update_data["name"])

    def test_update_token_queue_with_resource_type_be_location_as_user_without_write_permissions(
        self,
    ):
        """
        Test updating a token queue with resource type be location as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        location_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.facility_location,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=location_resource,
            is_primary=True,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Token Queue",
        }
        response = self.client.put(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    #  Tests for delete token queue

    def test_delete_token_queue_with_resource_type_be_practitioner_as_superuser(self):
        """dsss
        Test deleting a token queue with resource type be practitioner as superuser.
        """
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertIn(
            "No TokenQueue matches the given query.",
            str(get_response.data["errors"][0]["msg"]),
        )

    def test_delete_token_queue_with_resource_type_be_practitioner_as_user_with_permissions(
        self,
    ):
        """
        Test deleting a token queue with resource type be practitioner as a user with the required permissions.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertIn(
            "No TokenQueue matches the given query.",
            str(get_response.data["errors"][0]["msg"]),
        )

    def test_delete_token_queue_with_resource_type_be_practitioner_as_user_without_write_permissions(
        self,
    ):
        """
        Test deleting a token queue with resource type be practitioner as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    def test_delete_token_queue_with_resource_type_be_healthcare_service_as_superuser(
        self,
    ):
        """
        Test deleting a token queue with resource type be healthcare_service as superuser.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        healthcare_service_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=healthcare_service,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=healthcare_service_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertIn(
            "No TokenQueue matches the given query.",
            str(get_response.data["errors"][0]["msg"]),
        )

    def test_delete_token_queue_with_resource_type_be_healthcare_service_as_user_with_permissions(
        self,
    ):
        """
        Test deleting a token queue with resource type be healthcare_service as a user with the required permissions.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        healthcare_service_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=healthcare_service,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=healthcare_service_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertIn(
            "No TokenQueue matches the given query.",
            str(get_response.data["errors"][0]["msg"]),
        )

    def test_delete_token_queue_with_resource_type_be_healthcare_service_as_user_without_write_permissions(
        self,
    ):
        """
        Test deleting a token queue with resource type be healthcare_service as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        healthcare_service_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=healthcare_service,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=healthcare_service_resource,
            is_primary=True,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    def test_delete_token_queue_with_resource_type_be_location_as_superuser(self):
        """
        Test deleting a token queue with resource type be location as superuser.
        """
        location_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.facility_location,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=location_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertIn(
            "No TokenQueue matches the given query.",
            str(get_response.data["errors"][0]["msg"]),
        )

    def test_delete_token_queue_with_resource_type_be_location_as_user_with_permissions(
        self,
    ):
        """
        Test deleting a token queue with resource type be location as a user with the required permissions.
        """
        location_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.facility_location,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=location_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertIn(
            "No TokenQueue matches the given query.",
            str(get_response.data["errors"][0]["msg"]),
        )

    def test_delete_token_queue_with_resource_type_be_location_as_user_without_write_permissions(
        self,
    ):
        """
        Test deleting a token queue with resource type be location as a user without 'can_write_token' permissions.
        But is a part of facility organization.
        """
        location_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.facility_location,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=location_resource,
            is_primary=True,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )
