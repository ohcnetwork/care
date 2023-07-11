from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedBedRetrieveKeys(Enum):
    ID = "id"
    BED_TYPE = "bed_type"
    LOCATION_OBJECT = "location_object"
    IS_OCCUPIED = "is_occupied"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    DESCRIPTION = "description"
    META = "meta"


class ExpectedLocationObjectKeys(Enum):
    ID = "id"
    FACILITY = "facility"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    DESCRIPTION = "description"
    LOCATION_TYPE = "location_type"


class ExpectedFacilityKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedBedListKeys(Enum):
    ID = "id"
    BED_TYPE = "bed_type"
    DESCRIPTION = "description"
    NAME = "name"
    IS_OCCUPIED = "is_occupied"


class BedTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.bed = self.create_bed()

        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def tes_bed_retrieve(self):
        bedId = self.bed.external_id
        response = self.client.get(f"/api/v1/bed/{bedId}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertCountEqual(
            data.keys(), [item.value for item in ExpectedBedRetrieveKeys]
        )

        location_object_content = data["location_object"]

        if location_object_content is not None:
            self.assertCountEqual(
                location_object_content.keys(),
                [item.value for item in ExpectedLocationObjectKeys],
            )

        facility_content = location_object_content["facility"]

        if facility_content is not None:
            self.assertCountEqual(
                facility_content.keys(), [item.value for item in ExpectedFacilityKeys]
            )

    def test_bed_list(self):
        response = self.client.get("/api/v1/bed/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        results = data["results"]
        self.assertIsInstance(results, list)

        for bed in results:
            self.assertCountEqual(
                bed.keys(), [item.value for item in ExpectedBedListKeys]
            )
