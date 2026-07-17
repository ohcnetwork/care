from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models.scheduling.token import (
    Token,
    TokenCategory,
    TokenQueue,
    TokenSubQueue,
)
from care.emr.resources.scheduling.token.spec import TokenStatusOptions
from care.emr.signals.patient.facility_name_identifier import (
    FacilityPatientNameIdentifierConfig,
)
from care.emr.signals.patient.name_identifier import NameIdentifierConfig
from care.emr.signals.patient.phone_number_identifier import (
    PhoneNumberIdentifierConfig,
)
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenAPITests(CareAPITestBase):
    def setUp(self):
        NameIdentifierConfig.CACHED_CONFIG = {}
        PhoneNumberIdentifierConfig.CACHED_CONFIG = {}
        FacilityPatientNameIdentifierConfig.CACHED_CONFIG = {}
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.schedule_resource = self.create_schedule_resource(
            facility=self.facility, user=self.user
        )
        self.token_queue = self.create_queue(
            facility=self.facility,
            resource=self.schedule_resource,
            date=timezone.now().date(),
        )
        self.token_category = self.create_category(
            facility=self.facility, name="general"
        )

        self.token_url = self.generate_base_url(
            str(self.facility.external_id), str(self.token_queue.external_id)
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
                TokenPermissions.can_write_token.name,
            ]
        )

    def generate_base_url(self, facility, token_queue):
        return reverse(
            "queue-list",
            kwargs={
                "facility_external_id": facility,
                "token_queue_external_id": token_queue,
            },
        )

    def generate_detail_url(self, facility, token_queue, external_id):
        return reverse(
            "queue-detail",
            kwargs={
                "facility_external_id": facility,
                "token_queue_external_id": token_queue,
                "external_id": external_id,
            },
        )

    def generate_token_data(self, **kwargs):
        return {
            "patient": kwargs.get("patient"),
            "category": kwargs.get("category"),
            **kwargs,
        }

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def create_token(self, **kwargs):
        data = self.generate_token_data(**kwargs)
        return baker.make(Token, **data)

    def create_category(self, **kwargs):
        return baker.make(TokenCategory, **kwargs)

    def create_queue(self, **kwargs):
        return baker.make(TokenQueue, **kwargs)

    def create_subqueue(self, **kwargs):
        return baker.make(TokenSubQueue, **kwargs)

    # Tests for Token Creation

    def test_create_token_as_superuser(self):
        """Test creating a token as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        token_data = self.generate_token_data(
            patient=self.patient.external_id,
            category=self.token_category.external_id,
        )
        response = self.client.post(
            self.token_url,
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["number"], 1)
        self.assertEqual(
            get_response.data["category"]["id"],
            str(self.token_category.external_id),
        )
        self.assertEqual(
            get_response.data["patient"]["id"], str(self.patient.external_id)
        )
        self.assertEqual(get_response.data["status"], TokenStatusOptions.CREATED.value)

    def test_create_token_as_user_with_permission(self):
        """Test creating a token as a user with permission."""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token_data = self.generate_token_data(
            patient=self.patient.external_id,
            category=self.token_category.external_id,
        )
        response = self.client.post(
            self.token_url,
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["number"], 1)
        self.assertEqual(
            get_response.data["category"]["id"],
            str(self.token_category.external_id),
        )
        self.assertEqual(
            get_response.data["patient"]["id"], str(self.patient.external_id)
        )
        self.assertEqual(get_response.data["status"], TokenStatusOptions.CREATED.value)

    def test_create_token_as_user_without_permission(self):
        """Test creating a token as a user without permission."""
        self.client.force_authenticate(user=self.user)
        token_data = self.generate_token_data(
            patient=self.patient.external_id,
            category=self.token_category.external_id,
        )
        response = self.client.post(
            self.token_url,
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create token", response.data["detail"]
        )

    def test_create_token_with_different_facility_for_queue_and_category(self):
        """Test creating a token with different facility for queue and category."""
        another_facility = self.create_facility(user=self.superuser)
        category = self.create_category(facility=another_facility, name="special")
        self.client.force_authenticate(user=self.superuser)
        token_data = self.generate_token_data(
            patient=self.patient.external_id,
            category=category.external_id,
        )
        response = self.client.post(
            self.token_url,
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Category and Queue are not in the same facility",
            response.data["errors"][0]["msg"],
        )

    def test_create_token_with_different_facility_for_subqueue_and_queue(self):
        """Test creating a token with different facility for subqueue and queue."""
        another_facility = self.create_facility(user=self.superuser)
        subqueue = self.create_subqueue(
            facility=another_facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        self.client.force_authenticate(user=self.superuser)
        token_data = self.generate_token_data(
            patient=self.patient.external_id,
            category=self.token_category.external_id,
            sub_queue=subqueue.external_id,
        )
        response = self.client.post(
            self.token_url,
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Sub Queue and Queue are not in the same facility",
            response.data["errors"][0]["msg"],
        )

    def test_create_token_with_different_resource_for_subqueue_and_queue(self):
        """Test creating a token with different resource for subqueue and queue."""
        another_user = self.create_user()
        another_resource = self.create_schedule_resource(
            facility=self.facility, user=another_user
        )
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=another_resource,
            name="Sub Queue 1",
        )
        self.client.force_authenticate(user=self.superuser)
        token_data = self.generate_token_data(
            patient=self.patient.external_id,
            category=self.token_category.external_id,
            sub_queue=subqueue.external_id,
        )
        response = self.client.post(
            self.token_url,
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Sub Queue and Queue are not in the same resource",
            response.data["errors"][0]["msg"],
        )

    # Testcases for Token update

    def test_update_token_as_superuser(self):
        """Test updating a token as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token_data = {
            "status": TokenStatusOptions.IN_PROGRESS,
            "note": "Token is in progress",
            "sub_queue": subqueue.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], TokenStatusOptions.IN_PROGRESS.value)

    def test_update_token_as_user_with_permission(self):
        """Test updating a token as a user with permission."""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token_data = {
            "status": TokenStatusOptions.IN_PROGRESS,
            "note": "Token is in progress",
            "sub_queue": subqueue.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], TokenStatusOptions.IN_PROGRESS.value)

    def test_update_token_as_user_without_permission(self):
        """Test updating a token as a user without permission."""
        self.client.force_authenticate(user=self.user)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token_data = {
            "status": TokenStatusOptions.IN_PROGRESS,
            "note": "Token is in progress",
            "sub_queue": subqueue.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token",
            response.data["detail"],
        )

    def test_update_token_with_invalid_queue_without_url_resource_permission(self):
        """Test wrong-queue updates deny before exposing queue mismatch."""
        self.client.force_authenticate(user=self.user)
        actual_resource_user = self.create_user()
        self.attach_role_facility_organization_user(
            user=actual_resource_user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        actual_resource = self.create_schedule_resource(
            facility=self.facility,
            user=actual_resource_user,
        )
        actual_queue = self.create_queue(
            facility=self.facility,
            resource=actual_resource,
            date=timezone.now().date(),
        )
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=actual_queue,
            facility=self.facility,
        )
        url_resource = self.create_schedule_resource(
            facility=self.facility,
            user=self.create_user(),
        )
        url_queue = self.create_queue(
            facility=self.facility,
            resource=url_resource,
            date=timezone.now().date(),
        )
        token_data = {
            "status": TokenStatusOptions.IN_PROGRESS,
            "note": "Token is in progress",
            "sub_queue": None,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(url_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "You do not have permission to update token"
        )

    def test_update_token_with_different_facility_for_subqueue_and_queue(self):
        """Test updating a token with different facility for subqueue and queue."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        another_facility = self.create_facility(user=self.superuser)
        subqueue = self.create_subqueue(
            facility=another_facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token_data = {
            "sub_queue": subqueue.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Sub Queue and Queue are not in the same facility",
            response.data["errors"][0]["msg"],
        )

    def test_update_token_with_existing_sub_queue_with_different_resource_than_sub_queue(
        self,
    ):
        """Test updating a token with different resource for existing subqueue and subqueue."""
        self.client.force_authenticate(user=self.superuser)
        another_user = self.create_user()
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        another_resource = self.create_schedule_resource(
            facility=self.facility, user=another_user
        )
        subqueue1 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token.sub_queue = subqueue1
        token.save(update_fields=["sub_queue"])
        subqueue2 = self.create_subqueue(
            facility=self.facility,
            resource=another_resource,
            name="Sub Queue 2",
        )
        token_data = {
            "sub_queue": subqueue2.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Sub Queue and Queue are not in the same resource",
            response.data["errors"][0]["msg"],
        )

    def test_update_token_with_same_resource_for_new_subqueue(self):
        """Test updating a token with same resource for new subqueue."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        subqueue1 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token.sub_queue = subqueue1
        token.save(update_fields=["sub_queue"])
        subqueue2 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 2",
        )
        token_data = {
            "sub_queue": subqueue2.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sub_queue"]["id"], str(subqueue2.external_id))

    def test_update_token_with_existing_current_token_in_subqueue(self):
        """Test updating a token with existing current token in subqueue."""
        self.client.force_authenticate(user=self.superuser)
        token1 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
            current_token=token1,
        )
        token1.sub_queue = subqueue
        token1.save(update_fields=["sub_queue"])
        subqueue2 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 2",
        )
        token_data = {
            "sub_queue": subqueue2.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token1.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Sub Queue already has a current token",
            response.data["errors"][0]["msg"],
        )

    def test_update_token_with_current_token_as_null_in_subqueue(self):
        """Test updating a token with current token as null in subqueue."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
        )
        subqueue1 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
            current_token=None,
        )
        token.sub_queue = subqueue1
        token.save(update_fields=["sub_queue"])
        subqueue2 = self.create_subqueue(
            facility=self.facility, resource=self.schedule_resource, name="Sub Queue 2"
        )
        token_data = {
            "sub_queue": subqueue2.external_id,
        }
        response = self.client.put(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            ),
            data=token_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sub_queue"]["id"], str(subqueue2.external_id))

    # Tests for Token Retrieval

    def test_retrieve_token_as_superuser(self):
        """Test retrieving a token as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.get(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["category"]["id"],
            str(self.token_category.external_id),
        )
        self.assertEqual(response.data["patient"]["id"], str(self.patient.external_id))
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)

    def test_retrieve_token_as_user_with_permission(self):
        """Test retrieving a token as a user with permission."""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.get(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["category"]["id"],
            str(self.token_category.external_id),
        )
        self.assertEqual(response.data["patient"]["id"], str(self.patient.external_id))
        self.assertEqual(response.data["status"], TokenStatusOptions.CREATED.value)

    def test_retrieve_token_as_user_without_permission(self):
        """Test retrieving a token as a user without permission."""
        self.client.force_authenticate(user=self.user)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.get(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to read token", response.data["detail"]
        )

    def test_retrieve_token_with_invalid_queue_external_id(self):
        """Test retrieving a token with invalid queue external id."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        another_token_queue = self.create_queue(
            facility=self.facility,
            resource=self.schedule_resource,
            date=timezone.now().date(),
        )
        response = self.client.get(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(another_token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Token does not belong to the specified queue",
        )

    # Tests for Token Listing

    def test_list_tokens_as_superuser(self):
        """Test listing tokens as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        token1 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        token2 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
        )
        response = self.client.get(self.token_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        external_ids = [result["id"] for result in response.data["results"]]
        self.assertIn(str(token1.external_id), external_ids)
        self.assertIn(str(token2.external_id), external_ids)

    def test_list_tokens_as_user_with_permission(self):
        """Test listing tokens as a user with permission."""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token1 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        token2 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
        )
        response = self.client.get(self.token_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        external_ids = [result["id"] for result in response.data["results"]]
        self.assertIn(str(token1.external_id), external_ids)
        self.assertIn(str(token2.external_id), external_ids)

    def test_list_tokens_as_user_without_permission(self):
        """Test listing tokens as a user without permission."""
        self.client.force_authenticate(user=self.user)
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
        )
        response = self.client.get(self.token_url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list token", response.data["detail"]
        )

    def test_list_tokens_with_status_filter(self):
        """Test listing tokens with status filter."""
        self.client.force_authenticate(user=self.superuser)
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        token2 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
        )
        response = self.client.get(f"{self.token_url}?status=IN_PROGRESS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(token2.external_id))

    def test_list_tokens_with_subqueue_filter(self):
        """Test listing tokens with subqueue filter."""
        self.client.force_authenticate(user=self.superuser)
        subqueue1 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        subqueue2 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 2",
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
            sub_queue=subqueue1,
        )
        token2 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
            sub_queue=subqueue2,
        )
        response = self.client.get(
            f"{self.token_url}?sub_queue={subqueue2.external_id!s}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(token2.external_id))

    def test_list_tokens_with_subqueue_isnull_filter(self):
        """Test listing tokens with subqueue isnull filter."""
        self.client.force_authenticate(user=self.superuser)
        subqueue1 = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
            sub_queue=subqueue1,
        )
        token2 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
        )
        response = self.client.get(f"{self.token_url}?sub_queue_is_null=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(token2.external_id))

    def test_list_tokens_with_date_filter(self):
        """Test listing tokens with date filter."""
        self.client.force_authenticate(user=self.superuser)
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        token_queue = self.create_queue(
            facility=self.facility,
            resource=self.schedule_resource,
            date=yesterday,
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        token2 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.IN_PROGRESS,
        )
        response = self.client.get(f"{self.token_url}?date={today.isoformat()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(token2.external_id))

    #  Test cases for set next endpoint

    def test_set_next_token_as_superuser(self):
        """Test setting next token as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token1 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.post(
            reverse(
                "queue-set-next",
                kwargs={
                    "facility_external_id": str(self.facility.external_id),
                    "token_queue_external_id": str(self.token_queue.external_id),
                    "external_id": str(token1.external_id),
                },
            ),
            {"sub_queue": str(subqueue.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(token1.external_id))
        token1.refresh_from_db()
        self.assertEqual(token1.status, TokenStatusOptions.IN_PROGRESS)

    def test_set_next_token_as_user_with_permission(self):
        """Test setting next token as a user with permission."""
        self.client.force_authenticate(user=self.user)
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token1 = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.post(
            reverse(
                "queue-set-next",
                kwargs={
                    "facility_external_id": str(self.facility.external_id),
                    "token_queue_external_id": str(self.token_queue.external_id),
                    "external_id": str(token1.external_id),
                },
            ),
            {"sub_queue": str(subqueue.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(token1.external_id))
        token1.refresh_from_db()
        self.assertEqual(token1.status, TokenStatusOptions.IN_PROGRESS)

    def test_set_next_token_as_user_without_permission(self):
        """Test setting next token as a user without permission."""
        self.client.force_authenticate(user=self.user)
        subqueue = self.create_subqueue(
            facility=self.facility,
            resource=self.schedule_resource,
            name="Sub Queue 1",
        )
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.post(
            reverse(
                "queue-set-next",
                kwargs={
                    "facility_external_id": str(self.facility.external_id),
                    "token_queue_external_id": str(self.token_queue.external_id),
                    "external_id": str(token.external_id),
                },
            ),
            {"sub_queue": str(subqueue.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token", response.data["detail"]
        )

    # Tests for Token Deletion

    def test_delete_token_as_superuser(self):
        """Test deleting a token as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.delete(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 204)
        token.refresh_from_db()
        self.assertEqual(token.status, TokenStatusOptions.ENTERED_IN_ERROR)

    def test_delete_token_as_user_with_permission(self):
        """Test deleting a token as a user with permission."""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.delete(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 204)
        token.refresh_from_db()
        self.assertEqual(token.status, TokenStatusOptions.ENTERED_IN_ERROR)

    def test_delete_token_as_user_without_permission(self):
        """Test deleting a token as a user without permission."""
        self.client.force_authenticate(user=self.user)
        token = self.create_token(
            patient=self.patient,
            category=self.token_category,
            queue=self.token_queue,
            facility=self.facility,
            status=TokenStatusOptions.CREATED,
        )
        response = self.client.delete(
            self.generate_detail_url(
                str(self.facility.external_id),
                str(self.token_queue.external_id),
                str(token.external_id),
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update token", response.data["detail"]
        )
