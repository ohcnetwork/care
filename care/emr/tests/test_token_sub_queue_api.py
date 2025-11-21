from django.urls import reverse
from model_bakery import baker

from care.emr.models import FacilityLocation, FacilityLocationOrganization
from care.emr.models.scheduling.token import Token, TokenSubQueue
from care.emr.resources.scheduling.token.spec import SchedulableResourceTypeOptions
from care.emr.resources.scheduling.token_sub_queue.spec import (
    TokenSubQueueStatusOptions,
)
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenSubQueueAPITestCase(CareAPITestBase):
    """
    Test cases for TokenSubQueue API endpoints

    required fields:
    - resource_type eg: practitioner
    - resource_id eg: UUID of the practitioner

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
        self.user_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
        )
        self.patient = self.create_patient()
        self.location = self.create_facility_location(
            facility=self.facility, facility_organization=self.facility_organization
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
                TokenPermissions.can_write_token.name,
            ],
        )
        self.base_url = reverse(
            "token-sub-queue-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def generate_token_sub_detail_url(self, facility_external_id, external_id):
        return reverse(
            "token-sub-queue-detail",
            kwargs={
                "facility_external_id": facility_external_id,
                "external_id": external_id,
            },
        )

    def create_token(self, facility, **kwargs):
        return baker.make(Token, facility=facility, **kwargs)

    def create_token_sub_queue(self, facility, **kwargs):
        data = {
            "name": "General Sub Queue",
            "status": TokenSubQueueStatusOptions.active.value,
        }
        data.update(kwargs)
        return baker.make(TokenSubQueue, facility=facility, **data)

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def create_healthcare_service(self, **kwargs):
        return baker.make("emr.HealthcareService", **kwargs)

    def create_facility_location(self, facility, facility_organization, **kwargs):
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def generate_token_queue_data(self, **kwargs):
        data = {
            "name": kwargs.get("name") or "OP Room 1",
            "status": kwargs.get("status") or TokenSubQueueStatusOptions.active.value,
            "resource_type": kwargs.get("resource_type")
            or SchedulableResourceTypeOptions.practitioner.value,
            "resource_id": kwargs.get("resource_id") or str(self.superuser.external_id),
        }
        data.update(kwargs)
        return data

    # Test cases for create TokenSubQueue

    def test_create_token_sub_queue_as_superuser_for_resource_type_practitioner(self):
        """
        Test creating a token sub-queue as superuser for resource type practitioner
        """
        self.client.force_authenticate(user=self.superuser)
        payload = self.generate_token_queue_data()
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id, response.data["id"]
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["status"], response.data["status"])

    def test_create_token_sub_queue_as_normal_user_with_permissions_for_resource_type_practitioner(
        self,
    ):
        """
        Test creating a token sub-queue as normal user with permissions for resource type practitioner
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        payload = self.generate_token_queue_data(resource_id=str(self.user.external_id))
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id, response.data["id"]
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["status"], response.data["status"])

    def test_create_token_sub_queue_as_normal_user_without_permissions_for_resource_type_practitioner(
        self,
    ):
        """
        Test creating a token sub-queue as normal user without permissions for resource type practitioner
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ]
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        payload = self.generate_token_queue_data(resource_id=str(self.user.external_id))
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token sub queue",
            response.data["detail"],
        )

    def test_create_token_sub_queue_as_user_not_in_facility_organization_for_resource_type_practitioner(
        self,
    ):
        """
        Test creating a token sub-queue as normal user with permissions for resource type practitioner
        But not part of the facility organization
        """

        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        payload = self.generate_token_queue_data(resource_id=str(self.user.external_id))
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Schedule User is not part of the facility",
            response.data["errors"][0]["msg"],
        )

    def test_create_token_sub_queue_as_superuser_for_resource_type_healthcare(self):
        """
        Test creating a token sub-queue as superuser for resource type healthcare service
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        self.client.force_authenticate(user=self.superuser)
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id, response.data["id"]
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["status"], response.data["status"])

    def test_create_token_sub_queue_as_normal_user_with_permissions_for_resource_type_healthcare(
        self,
    ):
        """
        Test creating a token sub-queue as normal user with permissions for resource type healthcare service
        """
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id, response.data["id"]
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["status"], response.data["status"])

    def test_create_token_sub_queue_as_normal_user_without_permissions_for_resource_type_healthcare(
        self,
    ):
        """
        Test creating a token sub-queue as normal user without permissions for resource type healthcare service
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ]
        )
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token sub queue",
            response.data["detail"],
        )

    def test_create_token_sub_queue_as_user_not_in_facility_organization_for_resource_type_healthcare(
        self,
    ):
        """
        Test creating a token sub-queue as normal user with permissions for resource type healthcare service
        But not part of the facility organization
        """
        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        healthcare_service = self.create_healthcare_service(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token sub queue",
            response.data["detail"],
        )

    def test_create_token_sub_queue_with_healthcare_service_from_different_facility(
        self,
    ):
        """
        Test creating a token sub-queue with healthcare service from different facility
        """
        another_facility = self.create_facility(user=self.superuser)
        healthcare_service = self.create_healthcare_service(facility=another_facility)
        self.client.force_authenticate(user=self.superuser)
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(healthcare_service.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Healthcare Service is not part of the facility",
            response.data["errors"][0]["msg"],
        )

    def test_create_token_sub_queue_as_superuser_for_resource_type_location(self):
        """
        Test creating a token sub-queue as superuser for resource type location
        """

        self.client.force_authenticate(user=self.superuser)
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id, response.data["id"]
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["status"], response.data["status"])

    def test_create_token_sub_queue_as_user_with_permissions_for_resource_type_location(
        self,
    ):
        """
        Test creating a token sub-queue as normal user with permissions for resource type location
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id, response.data["id"]
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(response.data["id"]))
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["status"], response.data["status"])

    def test_create_token_sub_queue_as_user_without_permissions_for_resource_type_location(
        self,
    ):
        """
        Test creating a token sub-queue as normal user without permissions for resource type location
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ]
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token sub queue",
            response.data["detail"],
        )

    def test_create_token_sub_queue_as_user_not_in_facility_organization_for_resource_type_location(
        self,
    ):
        """
        Test creating a token sub-queue as normal user with permissions for resource type location
        But not part of the facility organization
        """
        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token sub queue",
            response.data["detail"],
        )

    def test_create_token_sub_queue_with_location_from_different_facility(self):
        """
        Test creating a token sub-queue with location from different facility
        """
        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        location = self.create_facility_location(
            facility=another_facility,
            facility_organization=another_facility_organization,
        )
        self.client.force_authenticate(user=self.superuser)
        payload = self.generate_token_queue_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(location.external_id),
        )
        response = self.client.post(self.base_url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Location is not part of the facility",
            response.data["errors"][0]["msg"],
        )

    # Test cases for update token sub-queue

    def test_update_token_sub_queue_as_superuser(self):
        """
        Test updating a token sub-queue as superuser
        """
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.superuser_resource
        )
        self.client.force_authenticate(user=self.superuser)
        payload = {
            "name": "Updated Sub Queue Name",
            "status": TokenSubQueueStatusOptions.inactive.value,
        }
        response = self.client.put(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            ),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_sub_queue.external_id))
        self.assertEqual(get_response.data["name"], payload["name"])
        self.assertEqual(get_response.data["status"], payload["status"])

    def test_update_token_sub_queue_as_user_with_permissions(self):
        """
        Test updating a token sub-queue as normal user with permissions
        """
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        payload = {
            "name": "Updated Sub Queue Name",
            "status": TokenSubQueueStatusOptions.inactive.value,
        }
        response = self.client.put(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            ),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(token_sub_queue.external_id))
        self.assertEqual(get_response.data["name"], payload["name"])
        self.assertEqual(get_response.data["status"], payload["status"])

    def test_update_token_sub_queue_as_user_without_permissions(self):
        """
        Test updating a token sub-queue as normal user without permissions
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ]
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        payload = {
            "name": "Updated Sub Queue Name",
            "status": TokenSubQueueStatusOptions.inactive.value,
        }
        response = self.client.put(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            ),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token sub queue",
            response.data["detail"],
        )

    def test_update_token_sub_queue_as_user_not_in_facility_organization(self):
        """
        Test updating a token sub-queue as normal user with permissions
        But not part of the facility organization
        """

        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        payload = {
            "name": "Updated Sub Queue Name",
            "status": TokenSubQueueStatusOptions.inactive.value,
        }
        response = self.client.put(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            ),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token sub queue",
            response.data["detail"],
        )

    # Test cases for retrieve token sub-queue

    def test_retrieve_token_sub_queue_as_superuser(self):
        """
        Test retrieving a token sub-queue as superuser
        """
        self.client.force_authenticate(user=self.superuser)
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.superuser_resource
        )
        response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(token_sub_queue.external_id))
        self.assertEqual(response.data["name"], token_sub_queue.name)
        self.assertEqual(response.data["status"], token_sub_queue.status)

    def test_retrieve_token_sub_queue_as_user_with_permissions(self):
        """
        Test retrieving a token sub-queue as normal user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(token_sub_queue.external_id))
        self.assertEqual(response.data["name"], token_sub_queue.name)
        self.assertEqual(response.data["status"], token_sub_queue.status)

    def test_retrieve_token_sub_queue_as_user_without_permissions(self):
        """
        Test retrieving a token sub-queue as normal user without permissions
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_write_token.name,
            ]
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )

        response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token sub queue",
            response.data["detail"],
        )

    def test_retrieve_token_sub_queue_as_user_not_in_facility_organization(self):
        """
        Test retrieving a token sub-queue as normal user with permissions
        But not part of the facility organization
        """

        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.superuser_resource
        )

        response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token sub queue",
            response.data["detail"],
        )

    def test_list_token_sub_queues_as_superuser(self):
        """
        Test listing token sub-queues as superuser
        """
        token_sub_queue1 = self.create_token_sub_queue(
            facility=self.facility, resource=self.superuser_resource
        )
        token_sub_queue2 = self.create_token_sub_queue(
            facility=self.facility, resource=self.superuser_resource
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {
                "resource_id": self.superuser.external_id,
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        returned_ids = {item["id"] for item in response.data["results"]}
        expected_ids = {
            str(token_sub_queue1.external_id),
            str(token_sub_queue2.external_id),
        }
        self.assertEqual(returned_ids, expected_ids)

    def test_list_token_sub_queues_as_user_with_permissions(self):
        """
        Test listing token sub-queues as normal user with permissions
        """
        token_sub_queue1 = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        token_sub_queue2 = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.base_url,
            {
                "resource_id": self.user.external_id,
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        returned_ids = {item["id"] for item in response.data["results"]}
        expected_ids = {
            str(token_sub_queue1.external_id),
            str(token_sub_queue2.external_id),
        }
        self.assertEqual(returned_ids, expected_ids)

    def test_list_token_sub_queues_as_user_without_permissions(self):
        """
        Test listing token sub-queues as normal user without permissions
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_write_token.name,
            ]
        )
        self.create_token_sub_queue(facility=self.facility, resource=self.user_resource)
        self.create_token_sub_queue(facility=self.facility, resource=self.user_resource)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.base_url,
            {
                "resource_id": self.user.external_id,
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token sub queue",
            response.data["detail"],
        )

    def test_list_token_sub_queues_without_resource_filter(self):
        """
        Test listing token sub-queues without resource filter
        """
        self.create_token_sub_queue(facility=self.facility, resource=self.user_resource)
        self.create_token_sub_queue(facility=self.facility, resource=self.user_resource)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "resource_type and resource_id is required",
            response.data["errors"][0]["msg"],
        )

    def test_list_token_sub_queues_with_name_filter(self):
        """
        Test listing token sub-queues with name filter
        """
        token_sub_queue1 = self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            name="OP Room A",
        )
        self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            name="OP Room B",
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.superuser.external_id,
                "name": "OP Room A",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(token_sub_queue1.external_id)
        )

    def test_list_token_sub_queues_with_status_filter(self):
        """
        Test listing token sub-queues with status filter
        """
        token_sub_queue1 = self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            status=TokenSubQueueStatusOptions.active.value,
        )
        self.create_token_sub_queue(
            facility=self.facility,
            resource=self.superuser_resource,
            status=TokenSubQueueStatusOptions.inactive.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": self.superuser.external_id,
                "status": TokenSubQueueStatusOptions.active.value,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(token_sub_queue1.external_id)
        )

    # Test cases for delete token sub-queue

    def test_delete_token_sub_queue_as_superuser(self):
        """
        Test deleting a token sub-queue as superuser
        """
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.superuser_resource
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)

    def test_delete_token_sub_queue_as_user_with_permissions(self):
        """
        Test deleting a token sub-queue as normal user with permissions
        """
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.delete(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 404)

    def test_delete_token_sub_queue_as_user_without_permissions(self):
        """
        Test deleting a token sub-queue as normal user without permissions
        But part of the facility organization
        """
        role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
            ]
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=role,
            user=self.user,
            facility_organization=self.facility_organization,
        )
        response = self.client.delete(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token sub queue",
            response.data["detail"],
        )

    def test_delete_token_sub_queue_as_user_not_in_facility_organization(self):
        """
        Test deleting a token sub-queue as normal user with permissions
        But not part of the facility organization
        """

        another_facility = self.create_facility(user=self.superuser)
        another_facility_organization = self.create_facility_organization(
            facility=another_facility,
            org_type="root",
        )
        token_sub_queue = self.create_token_sub_queue(
            facility=self.facility, resource=self.user_resource
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=another_facility_organization,
        )
        response = self.client.delete(
            self.generate_token_sub_detail_url(
                self.facility.external_id,
                token_sub_queue.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token sub queue",
            response.data["detail"],
        )
