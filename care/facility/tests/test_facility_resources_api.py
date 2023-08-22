from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedResourcesListKeys(Enum):
    id = "id"
    status = "status"
    origin_facility_object = "origin_facility_object"
    approving_facility_object = "approving_facility_object"
    assigned_facility_object = "assigned_facility_object"
    external_id = "external_id"
    emergency = "emergency"
    title = "title"


class OriginFacilityKeys(Enum):
    id = "id"
    name = "name"


class ApprovingFacilityKeys(Enum):
    id = "id"
    name = "name"


class AssignedFacilityKeys(Enum):
    id = "id"
    name = "name"


class FacilityObjectKeys(Enum):
    id = "id"
    name = "name"
    local_body = "local_body"
    district = "district"
    state = "state"
    ward_object = "ward_object"
    local_body_object = "local_body_object"
    district_object = "district_object"
    state_object = "state_object"
    facility_type = "facility_type"
    read_cover_image_url = "read_cover_image_url"
    features = "features"
    patient_count = "patient_count"
    bed_count = "bed_count"


class UserObjectKeys(Enum):
    id = "id"
    first_name = "first_name"
    username = "username"
    email = "email"
    last_name = "last_name"
    user_type = "user_type"
    last_login = "last_login"


class ExpectedResourcesRetrieveKeys(Enum):
    id = "id"
    status = "status"
    origin_facility_object = "origin_facility_object"
    approving_facility_object = "approving_facility_object"
    assigned_facility_object = "assigned_facility_object"
    category = "category"
    sub_category = "sub_category"
    origin_facility = "origin_facility"
    approving_facility = "approving_facility"
    assigned_facility = "assigned_facility"
    assigned_to_object = "assigned_to_object"
    created_by_object = "created_by_object"
    last_edited_by_object = "last_edited_by_object"
    external_id = "external_id"
    created_date = "created_date"
    modified_date = "modified_date"
    emergency = "emergency"
    title = "title"
    reason = "reason"
    refering_facility_contact_name = "refering_facility_contact_name"
    refering_facility_contact_number = "refering_facility_contact_number"
    priority = "priority"
    requested_quantity = "requested_quantity"
    assigned_quantity = "assigned_quantity"
    is_assigned_to_user = "is_assigned_to_user"
    assigned_to = "assigned_to"
    created_by = "created_by"
    last_edited_by = "last_edited_by"


class ExpectedResourceCommentListKeys(Enum):
    id = "id"
    comment = "comment"
    modified_date = "modified_date"
    created_by_object = "created_by_object"


class ExpectedUserResourceCommentListKeys(Enum):
    id = "id"
    first_name = "first_name"
    last_name = "last_name"


class ExpectedResourceCommentRetrieveKeys(Enum):
    id = "id"
    created_by_object = "created_by_object"
    external_id = "external_id"
    created_date = "created_date"
    modified_date = "modified_date"
    comment = "comment"
    created_by = "created_by"


class ExpectedUserResourceCommentRetrieveKeys(Enum):
    id = "id"
    first_name = "first_name"
    last_name = "last_name"
    username = "username"
    email = "email"
    user_type = "user_type"
    last_login = "last_login"


class ResourceRequestViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        cls.resource = cls.create_resource()

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_resources(self):
        response = self.client.get("/api/v1/resource/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        expected_keys = [key.value for key in ExpectedResourcesListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        origin_facility_keys = [key.value for key in OriginFacilityKeys]
        approving_facility_keys = [key.value for key in ApprovingFacilityKeys]
        assigned_facility_keys = [key.value for key in AssignedFacilityKeys]

        origin_facility_object = data["origin_facility_object"]
        approving_facility_object = data["approving_facility_object"]
        assigned_facility_object = data["assigned_facility_object"]

        self.assertCountEqual(origin_facility_object.keys(), origin_facility_keys)
        self.assertCountEqual(approving_facility_object.keys(), approving_facility_keys)
        self.assertCountEqual(assigned_facility_object.keys(), assigned_facility_keys)

    def test_retrieve_resource(self):
        response = self.client.get(f"/api/v1/resource/{self.resource.external_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [key.value for key in ExpectedResourcesRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        origin_facility_keys = [key.value for key in FacilityObjectKeys]
        approving_facility_keys = [key.value for key in FacilityObjectKeys]
        assigned_facility_keys = [key.value for key in FacilityObjectKeys]

        origin_facility_object = data["origin_facility_object"]
        approving_facility_object = data["approving_facility_object"]
        assigned_facility_object = data["assigned_facility_object"]

        self.assertCountEqual(origin_facility_object.keys(), origin_facility_keys)
        self.assertCountEqual(approving_facility_object.keys(), approving_facility_keys)
        self.assertCountEqual(assigned_facility_object.keys(), assigned_facility_keys)

        assigned_to_keys = [key.value for key in UserObjectKeys]
        created_by_object_keys = [key.value for key in UserObjectKeys]
        last_edited_by_object_keys = [key.value for key in UserObjectKeys]

        assigned_to_object = data["assigned_to_object"]
        created_by_object = data["created_by_object"]
        last_edited_by_object = data["last_edited_by_object"]

        self.assertCountEqual(assigned_to_object.keys(), assigned_to_keys)
        self.assertCountEqual(created_by_object.keys(), created_by_object_keys)
        self.assertCountEqual(last_edited_by_object.keys(), last_edited_by_object_keys)


class ResourceRequestCommentViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_resource_comment(self):
        response = self.client.get(
            f"/api/v1/resource/{self.resource.external_id}/comment/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        expected_keys = [key.value for key in ExpectedResourceCommentListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        created_by_object_keys = [
            key.value for key in ExpectedUserResourceCommentListKeys
        ]
        created_by_object = data["created_by_object"]
        self.assertCountEqual(created_by_object.keys(), created_by_object_keys)

    def test_retrieve_resource_comment(self):
        response = self.client.get(
            f"/api/v1/resource/{self.resource.external_id}/comment/{self.resource_comment.external_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [key.value for key in ExpectedResourceCommentRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        created_by_object_keys = [
            key.value for key in ExpectedUserResourceCommentRetrieveKeys
        ]
        created_by_object = data["created_by_object"]
        self.assertCountEqual(created_by_object.keys(), created_by_object_keys)
