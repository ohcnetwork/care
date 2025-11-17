from datetime import timedelta
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models import FacilityLocation, FacilityLocationOrganization
from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.scheduling.token import (
    Token,
    TokenCategory,
    TokenQueue,
    TokenSubQueue,
)
from care.emr.resources.scheduling.token.spec import (
    SchedulableResourceTypeOptions,
    TokenStatusOptions,
)
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
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def create_healthcare_service(self, facility, **kwargs):
        return baker.make(HealthcareService, facility=facility, **kwargs)

    def create_token(self, facility, **kwargs):
        return baker.make(Token, facility=facility, **kwargs)

    def create_token_category(self, facility, **kwargs):
        return baker.make(TokenCategory, facility=facility, **kwargs)

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

    def test_create_token_queue_with_an_existing_primary_queue(self):
        """
        Test creating a token queue with an existing primary queue.
        """
        self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
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
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(get_response.data["is_primary"], False)

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

    #  tests for retrieve token queue

    def test_retrieve_token_queue_as_superuser(self):
        """
        Test retrieving a token queue as superuser.
        """
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Initial Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(token_queue.external_id))
        self.assertEqual(response.data["name"], token_queue.name)

    def test_retrieve_token_queue_as_user_with_permissions(self):
        """
        Test retrieving a token queue as a user with the required permissions.
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
        response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(token_queue.external_id))
        self.assertEqual(response.data["name"], token_queue.name)

    def test_retrieve_token_queue_as_user_without_permissions(self):
        """
        Test retrieving a token queue as a user without the required permissions.
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
        response = self.client.get(
            self.generate_detail_url(
                facility_external_id=self.facility.external_id,
                external_id=token_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token queue", str(response.data)
        )

    # tests for list token queue

    def test_list_token_queues_with_resource_type_be_practitioner_as_superuser(self):
        """
        Test listing token queues with resource_type as practitioner for superuser.
        """
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        token_queue2 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=2)).date(),
            resource=self.superuser_resource,
            is_primary=False,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.superuser.external_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(token_queue1.external_id), returned_ids)
        self.assertIn(str(token_queue2.external_id), returned_ids)

    def test_list_token_queues_as_user_with_permissions(self):
        """
        Test listing token queues as a user with the required permissions.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        token_queue2 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=2)).date(),
            resource=user_resource,
            is_primary=False,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.user.external_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(token_queue1.external_id), returned_ids)
        self.assertIn(str(token_queue2.external_id), returned_ids)

    def test_list_token_queues_as_user_without_permissions(self):
        """
        Test listing token queues as a user without the required permissions.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_write_token.name,
            ]
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=role,
            facility_organization=self.facility_organization,
        )

        self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=2)).date(),
            resource=user_resource,
            is_primary=False,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.user.external_id,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token queue", str(response.data)
        )

    def test_list_token_queues_without_resource_type_and_resource_id(self):
        """
        Test listing token queues without resource_type and resource_id.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "resource_type and resource_id is required",
            str(response.data),
        )

    def test_list_token_queues_without_resource(self):
        """
        Test listing token queues for a resource with no token queues.
        """
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.user.external_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_token_queue_with_name_filter(self):
        """
        Test listing token queues with a name filter.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=2)).date(),
            resource=user_resource,
            is_primary=False,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.user.external_id,
                "name": "Token Queue 1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(token_queue1.external_id)
        )

    def test_list_token_queue_with_date_filter(self):
        """
        Test listing token queues with a date filter.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=2)).date(),
            resource=user_resource,
            is_primary=False,
        )
        self.client.force_authenticate(user=self.user)
        filter_date = (timezone.now() + timedelta(days=1)).date().isoformat()
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.user.external_id,
                "date": filter_date,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(token_queue1.external_id)
        )

    # Test cases for is primary field behavior

    def test_create_token_queue_sets_is_primary_true_as_superuser(self):
        """
        Test that creating a token queue the primary queue with an existing queue as primary.
        """
        self.client.force_authenticate(user=self.superuser)
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        token_queue2 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=False,
        )
        self.url = reverse(
            "token-queue-set-primary",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": token_queue2.external_id,
            },
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        token_queue1.refresh_from_db()
        token_queue2.refresh_from_db()
        self.assertFalse(token_queue1.is_primary)
        self.assertTrue(token_queue2.is_primary)

    def test_create_token_queue_sets_is_primary_true_as_user_with_permissions(self):
        """
        Test that creating a token queue the primary queue with an existing queue as primary by a user with permissions.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        token_queue2 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=False,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.url = reverse(
            "token-queue-set-primary",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": token_queue2.external_id,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        token_queue1.refresh_from_db()
        token_queue2.refresh_from_db()
        self.assertFalse(token_queue1.is_primary)
        self.assertTrue(token_queue2.is_primary)

    def test_create_token_queue_sets_is_primary_true_as_user_without_permissions(self):
        """
        Test that creating a token queue the primary queue with an existing queue as primary by a user without permissions.
        """
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue1 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        token_queue2 = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 2",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=False,
        )
        self.url = reverse(
            "token-queue-set-primary",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": token_queue2.external_id,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        token_queue1.refresh_from_db()
        token_queue2.refresh_from_db()
        self.assertTrue(token_queue1.is_primary)
        self.assertFalse(token_queue2.is_primary)

    # Tests for generate summary endpoint

    def test_generate_summary_for_token_as_superuser(self):
        """
        Test generating summary for tokens as superuser.
        """
        token_category = self.create_token_category(
            facility=self.facility,
            name="General",
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            shorthand="GEN",
            default=True,
        )

        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=2,
            status=TokenStatusOptions.IN_PROGRESS.value,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=3,
            status=TokenStatusOptions.FULFILLED.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = reverse(
            "token-queue-summary",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": token_queue.external_id,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("General", response.data)
        category_summary = response.data["General"]
        self.assertEqual(category_summary["CREATED"], 1)
        self.assertEqual(category_summary["IN_PROGRESS"], 1)
        self.assertEqual(category_summary["FULFILLED"], 1)

    def test_generate_summary_for_token_as_user_with_permission(self):
        """
        Test generating summary for tokens as a user with the required permissions.
        """
        token_category = self.create_token_category(
            facility=self.facility,
            name="General",
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            shorthand="GEN",
            default=True,
        )

        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )

        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=2,
            status=TokenStatusOptions.IN_PROGRESS.value,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=3,
            status=TokenStatusOptions.FULFILLED.value,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "token-queue-summary",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": token_queue.external_id,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("General", response.data)
        category_summary = response.data["General"]
        self.assertEqual(category_summary["CREATED"], 1)
        self.assertEqual(category_summary["IN_PROGRESS"], 1)
        self.assertEqual(category_summary["FULFILLED"], 1)

    def test_generate_summary_for_token_as_user_without_permission(self):
        """
        Test generating summary for tokens as a user without the required permissions.
        """
        token_category = self.create_token_category(
            facility=self.facility,
            name="General",
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            shorthand="GEN",
            default=True,
        )

        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )

        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Token Queue 1",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=2,
            status=TokenStatusOptions.IN_PROGRESS.value,
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=token_category,
            number=3,
            status=TokenStatusOptions.FULFILLED.value,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "token-queue-summary",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": token_queue.external_id,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token queue", str(response.data)
        )


class TokenQueueAPIGenerateTokenTestCase(CareAPITestBase):
    """
    Test case for generating tokens via the generate token endpoint.

    fields:
    - patient: UUID4
    - category: UUID4
    - note: str
    - sub_queue: UUID4

    - resource_type: SchedulableResourceTypeOptions
    - resource_id: UUID4
    - date: date

    'can_write_token' permission is required to generate tokens.

    resource types supported:
    - practitioner
    - healthcare_service
    - location

    """

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

        self.token_category = self.create_token_category(
            name="General",
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            shorthand="GEN",
            default=True,
        )
        self.base_url = reverse(
            "token-queue-generate-token",
            kwargs={"facility_external_id": self.facility.external_id},
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

    def create_token_category(self, facility, **kwargs):
        return baker.make(TokenCategory, facility=facility, **kwargs)

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def create_healthcare_service(self, facility, **kwargs):
        return baker.make(HealthcareService, facility=facility, **kwargs)

    def create_token_queue(self, facility, **kwargs):
        return baker.make(TokenQueue, facility=facility, **kwargs)

    def test_generate_token_for_resource_type_be_practitioner_as_superuser(self):
        """
        Test generating a token for resource type 'practitioner' as superuser.
        """

        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.superuser.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_practitioner_as_user_with_permissions(
        self,
    ):
        """
        Test generating a token for resource type 'practitioner' as a user with the required permissions.
        """
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_practitioner_as_user_without_permissions(
        self,
    ):
        """
        Test generating a token for resource type 'practitioner' as a user without the 'can_write_token' permissions.
        But the user is part of the facility organization.
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
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_generate_token_for_resource_type_be_practitioner_as_user_not_in_facility_organization(
        self,
    ):
        """
        Test generating a token for resource type 'practitioner' as a user without the 'can_write_token' permissions.
        And the user is not part of the facility organization.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Schedule User is not part of the facility", str(response.data))

    def test_generate_token_creates_primary_queue_if_not_exists(self):
        """
        Test that generating a token creates a primary token queue if it does not exist.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.superuser.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        token_queue_id = response.data["queue"]["id"]
        token_queue = TokenQueue.objects.get(external_id=token_queue_id)
        self.assertTrue(token_queue.is_primary)
        self.assertEqual(token_queue.resource, self.superuser_resource)
        self.assertEqual(token_queue.date, (timezone.now() + timedelta(days=1)).date())
        self.assertEqual(token_queue.name, "System Generated")
        self.assertTrue(token_queue.system_generated)

    def test_generate_token_creates_with_primary_queue(self):
        """
        Test that generating a token uses the existing primary token queue.
        """
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Primary Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.superuser.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        queue = response.data["queue"]
        self.assertEqual(queue["id"], str(token_queue.external_id))
        self.assertTrue(queue["is_primary"])
        self.assertFalse(queue["system_generated"])

    def test_generate_token_assigns_incremental_token_numbers(self):
        """
        Test that generating multiple tokens assigns incremental token numbers within the same queue and category.
        """
        self.client.force_authenticate(user=self.superuser)
        for i in range(1, 6):
            response = self.client.post(
                self.base_url,
                {
                    "patient": str(self.patient.external_id),
                    "category": str(self.token_category.external_id),
                    "note": f"Test token note {i}",
                    "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                    "resource_id": str(self.superuser.external_id),
                    "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
                },
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["number"], i)
            self.assertEqual(response.data["note"], f"Test token note {i}")

    def test_generate_token_with_invalid_category(self):
        """
        Test generating a token with an invalid category UUID.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(uuid4()),  # Invalid category
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.superuser.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("No TokenCategory matches the given query.", str(response.data))

    def test_generate_token_with_invalid_patient(self):
        """
        Test generating a token with an invalid patient UUID.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(uuid4()),  # Invalid patient
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.superuser.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("No Patient matches the given query.", str(response.data))

    def test_generate_token_without_patient(self):
        """
        Test generating a token without providing a patient UUID.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.superuser.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_healthcare_service_as_superuser(self):
        """
        Test generating a token for resource type 'healthcare_service' as superuser.
        """
        healthcare_service = self.create_healthcare_service(
            facility=self.facility,
            name="Test Healthcare Service",
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.healthcare_service.value,
                "resource_id": str(healthcare_service.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_healthcare_service_as_user_with_permissions(
        self,
    ):
        """
        Test generating a token for resource type 'healthcare_service' as a user with the required permissions.
        """
        healthcare_service = self.create_healthcare_service(
            facility=self.facility,
            name="Test Healthcare Service",
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.healthcare_service.value,
                "resource_id": str(healthcare_service.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_healthcare_service_as_user_without_permissions(
        self,
    ):
        """
        Test generating a token for resource type 'healthcare_service' as a user without the 'can_write_token' permissions.
        But the user is part of the facility organization.
        """
        healthcare_service = self.create_healthcare_service(
            facility=self.facility,
            name="Test Healthcare Service",
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
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.healthcare_service.value,
                "resource_id": str(healthcare_service.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_generate_token_for_resource_type_be_healthcare_service_as_user_not_in_facility_organization(
        self,
    ):
        """
        Test generating a token for resource type 'healthcare_service' as a user without the 'can_write_token' permissions.
        And the user is not part of the facility organization.
        """
        healthcare_service = self.create_healthcare_service(
            facility=self.facility,
            name="Test Healthcare Service",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.healthcare_service.value,
                "resource_id": str(healthcare_service.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_generate_token_for_resource_type_be_healthcare_service_outside_facility_as_user(
        self,
    ):
        """
        Test generating a token for resource type 'healthcare_service' with service outside the facility as user.
        """
        another_facility = self.create_facility(
            user=self.superuser, name="Another Facility"
        )
        healthcare_service = self.create_healthcare_service(
            facility=another_facility,
            name="Outside Healthcare Service",
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.healthcare_service.value,
                "resource_id": str(healthcare_service.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Healthcare Service is not part of the facility", str(response.data)
        )

    def test_generate_token_for_resource_type_be_location_as_superuser(self):
        """
        Test generating a token for resource type 'location' as superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.location.value,
                "resource_id": str(self.facility_location.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_location_as_user_with_permissions(
        self,
    ):
        """
        Test generating a token for resource type 'location' as a user with the required permissions.
        """
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.location.value,
                "resource_id": str(self.facility_location.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["note"], "Test token note")
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)
        self.assertEqual(response.data["number"], 1)

    def test_generate_token_for_resource_type_be_location_as_user_without_permissions(
        self,
    ):
        """
        Test generating a token for resource type 'location' as a user without the 'can_write_token' permissions.
        But the user is part of the facility organization.
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
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.location.value,
                "resource_id": str(self.facility_location.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_generate_token_for_resource_type_be_location_as_user_not_in_facility_organization(
        self,
    ):
        """
        Test generating a token for resource type 'location' as a user without the 'can_write_token' permissions.
        But the user is not part of the facility organization.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.location.value,
                "resource_id": str(self.facility_location.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token queue", str(response.data)
        )

    def test_generate_token_for_resource_type_be_location_outside_facility_organization_as_user(
        self,
    ):
        """
        Test generating a token for resource type 'location' with location outside the facility organization as user.
        """
        another_facility = self.create_facility(
            user=self.superuser, name="Another Facility"
        )
        another_facility_organization = self.create_facility_organization(
            facility=another_facility, org_type="root"
        )
        location = self.create_facility_location(
            facility=another_facility,
            facility_organization=another_facility_organization,
            name="Outside Location",
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            {
                "patient": str(self.patient.external_id),
                "category": str(self.token_category.external_id),
                "note": "Test token note",
                "resource_type": SchedulableResourceTypeOptions.location.value,
                "resource_id": str(location.external_id),
                "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Location is not part of the facility", str(response.data))


class TokenQueueSetNextTokenToSubQueueTestCase(CareAPITestBase):
    """
    Test case for setting the next token to a sub-queue via the sub-queue next token endpoint.

    fields:
    - sub_queue: UUID4
    - category: UUID4

    'can_write_token' permission is required to set the next token to a sub-queue.

    Supported resource types:

    - practitioner
    - healthcare_service
    - location

    """

    def setUp(self):
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.superuser_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.superuser,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
                TokenPermissions.can_write_token.name,
            ],
        )

        self.token_category = self.create_token_category(
            name="General",
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            shorthand="GEN",
            default=True,
        )

    def create_token_category(self, facility, **kwargs):
        return baker.make(TokenCategory, facility=facility, **kwargs)

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def create_token_queue(self, facility, **kwargs):
        return baker.make(TokenQueue, facility=facility, **kwargs)

    def create_token_sub_queue(self, facility, resource, **kwargs):
        return baker.make(TokenSubQueue, facility=facility, resource=resource, **kwargs)

    def create_token(self, facility, **kwargs):
        return baker.make(Token, facility=facility, **kwargs)

    def generate_url(self, facility_external_id, external_id):
        return reverse(
            "token-queue-set-next-token-to-subqueue",
            kwargs={
                "facility_external_id": str(facility_external_id),
                "external_id": str(external_id),
            },
        )

    def test_set_next_token_to_subqueue_as_superuser(self):
        """
        Test setting the next token to a sub-queue as superuser.

        needs to create:
        - token queue
        - token sub-queue
        - token
        """
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Primary Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        sub_queue = self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            name="Sub Queue 1",
            status="active",
        )
        token = self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=self.token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_url(self.facility.external_id, token_queue.external_id)
        response = self.client.post(
            url,
            {
                "sub_queue": str(sub_queue.external_id),
                "category": str(self.token_category.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        sub_queue.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual(sub_queue.current_token, token)
        self.assertEqual(token.status, TokenStatusOptions.IN_PROGRESS.value)

    def test_set_next_token_to_subqueue_as_user_with_permissions(self):
        """
        Test setting the next token to a sub-queue as a user with the required permissions.

        needs to create:
        - token queue
        - token sub-queue
        - token
        """
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Primary Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=user_resource,
            is_primary=True,
        )
        sub_queue = self.create_token_sub_queue(
            facility=self.facility,
            resource=user_resource,
            name="Sub Queue 1",
            status="active",
        )
        token = self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=self.token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_url(self.facility.external_id, token_queue.external_id)
        response = self.client.post(
            url,
            {
                "sub_queue": str(sub_queue.external_id),
                "category": str(self.token_category.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        sub_queue.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual(sub_queue.current_token, token)
        self.assertEqual(token.status, TokenStatusOptions.IN_PROGRESS.value)

    def test_set_next_token_to_subqueue_as_user_without_permissions(self):
        """
        Test setting the next token to a sub-queue as a user without the 'can_write_token' permissions.

        needs to create:
        - token queue
        - token sub-queue
        - token
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ],
        )
        self.attach_role_facility_organization_user(
            user=self.user, role=role, facility_organization=self.facility_organization
        )
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Primary Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        sub_queue = self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            name="Sub Queue 1",
            status="active",
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=self.token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_url(self.facility.external_id, token_queue.external_id)
        response = self.client.post(
            url,
            {
                "sub_queue": str(sub_queue.external_id),
                "category": str(self.token_category.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token queue", str(response.data)
        )

    def test_set_next_token_to_subqueue_with_an_category_outside_facility(self):
        """
        Test setting the next token to a sub-queue with category outside the facility.
        """
        another_facility = self.create_facility(
            user=self.superuser, name="Another Facility"
        )
        token_category = self.create_token_category(
            name="Special",
            facility=another_facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            shorthand="SPC",
            default=False,
        )
        self.client.force_authenticate(user=self.superuser)
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Primary Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        sub_queue = self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            name="Sub Queue 1",
            status="active",
        )
        self.create_token(
            facility=self.facility,
            queue=token_queue,
            category=self.token_category,
            number=1,
            status=TokenStatusOptions.CREATED.value,
        )
        url = self.generate_url(self.facility.external_id, token_queue.external_id)
        response = self.client.post(
            url,
            {
                "sub_queue": str(sub_queue.external_id),
                "category": str(token_category.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("No TokenCategory matches the given query.", str(response.data))

    def test_set_next_token_to_subqueue_with_no_available_tokens(self):
        """
        Test setting the next token to a sub-queue when there are no available tokens in the queue for the given category.
        """
        self.client.force_authenticate(user=self.superuser)
        token_queue = self.create_token_queue(
            facility=self.facility,
            name="Primary Token Queue",
            date=(timezone.now() + timedelta(days=1)).date(),
            resource=self.superuser_resource,
            is_primary=True,
        )
        sub_queue = self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            name="Sub Queue 1",
            status="active",
        )
        url = self.generate_url(self.facility.external_id, token_queue.external_id)
        response = self.client.post(
            url,
            {
                "sub_queue": str(sub_queue.external_id),
                "category": str(self.token_category.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No tokens found", str(response.data))
