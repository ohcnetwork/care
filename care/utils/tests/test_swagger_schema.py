from django.test import TestCase
from rest_framework import status


class SwaggerSchemaTest(TestCase):
    def test_swagger_endpoint(self):
        response = self.client.get("/swagger/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
