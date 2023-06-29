from django.test import TestCase
from rest_framework import status
from care.facility.api.viewsets.bed import BedViewSet
from care.facility.tests.mixins import TestClassMixin

class SingleBedTest(TestClassMixin, TestCase):
    def test_create(self):
        user = self.users[0]
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": "657c32be-d584-476c-9ce2-0412f0e7692e",
            "location": "7f0c2bba-face-47f1-a547-87617a8c9b04",
            "name": "Test Bed",
            "number_of_beds": 1,
        }
        response = self.new_request(
            ("/api/v1/bed/", sample_data, "json"),
            {"post": "create"},
            BedViewSet,
            user
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)