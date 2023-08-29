from rest_framework import status

from care.utils.tests.test_base import TestBase


class TestMedibaseApi(TestBase):
    def get_url(self, query=None):
        return f"/api/v1/medibase/?query={query}"

    def test_search_by_name_exact_word(self):
        response = self.client.get(self.get_url(query="dolo"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "DOLO")

    def test_search_by_generic_exact(self):
        response = self.client.get(self.get_url(query="pAraCetAmoL"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "paracetamol")

    def test_search_by_name_and_generic_exact_word(self):
        response = self.client.get(self.get_url(query="panadol paracetamol"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "PANADOL")
        self.assertEqual(response.data[0]["generic"], "paracetamol")
        self.assertEqual(response.data[0]["company"], "GSK")
