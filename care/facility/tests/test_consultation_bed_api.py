from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from care.utils.tests.test_base import TestBase


class ExpectedConsultationBedRetrieveKeys(Enum):
    ID = "id"
    BED_OBJECT = "bed_object"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    START_DATE = "start_date"
    END_DATE = "end_date"
    META = "meta"


class ExpectedBedKeys(Enum):
    ID = "id"
    BED_TYPE = "bed_type"
    IS_OCCUPIED = "is_occupied"
    LOCATION_OBJECT = "location_object"
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


class ExpectedConsultationBedListKeys(Enum):
    ID = "id"
    BED_OBJECT = "bed_object"
    START_DATE = "start_date"
    END_DATE = "end_date"


class ExpectedBareMinimumBedKeys(Enum):
    ID = "id"
    NAME = "name"
    LOCATION_OBJECT = "location_object"


class ExpectedBareMinimumLocationObjectKeys(Enum):
    ID = "id"
    NAME = "name"


class ConsultationBedTestCase(TestBase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.consultation_bed = self.create_consultation_bed()

        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_consultation_bed_retrieve(self):
        bedAssignmentId = self.consultation_bed.external_id
        response = self.client.get(f"/api/v1/consultationbed/{bedAssignmentId}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertCountEqual(
            data.keys(), [item.value for item in ExpectedConsultationBedRetrieveKeys]
        )

        bed_object_content = data["bed_object"]

        if bed_object_content is not None:
            self.assertCountEqual(
                bed_object_content.keys(), [item.value for item in ExpectedBedKeys]
            )

        location_object_content = bed_object_content["location_object"]

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

    def test_consultation_bed_list(self):
        response = self.client.get("/api/v1/consultationbed/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        results = data["results"]
        self.assertIsInstance(results, list)

        for consultation_bed in results:
            self.assertCountEqual(
                consultation_bed.keys(),
                [item.value for item in ExpectedConsultationBedListKeys],
            )

            bed_object_content = consultation_bed["bed_object"]

            if bed_object_content is not None:
                self.assertCountEqual(
                    bed_object_content.keys(),
                    [item.value for item in ExpectedBareMinimumBedKeys],
                )

            location_object_content = bed_object_content["location_object"]

            if location_object_content is not None:
                self.assertCountEqual(
                    location_object_content.keys(),
                    [item.value for item in ExpectedBareMinimumLocationObjectKeys],
                )
