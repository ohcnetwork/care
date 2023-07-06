from rest_framework import status

from care.utils.tests.test_base import TestBase


class TestMedibaseApi(TestBase):
    def get_url(self, query=None):
        return f"/api/v1/medicine/?search_text={query}"

    def test_search_by_name_exact_word(self):
        response = self.client.get(self.get_url(query="dolo"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data.results[0]["name"], "DOLO")

    def test_search_by_generic_exact_word(self):
        response = self.client.get(self.get_url(query="pAraCetAmoL"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data.results[0]["generic"], "paracetamol")

    def test_search_by_name_and_generic_exact_word(self):
        response = self.client.get(self.get_url(query="panadol paracetamol"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data.results[0]["name"], "PANADOL")
        self.assertEquals(response.data.results[0]["generic"], "paracetamol")
        self.assertEquals(response.data.results[0]["company"], "GSK")
