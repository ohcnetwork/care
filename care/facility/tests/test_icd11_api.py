from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class TestICD11Api(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user(
            "icd11_doctor", cls.district, home_facility=cls.facility
        )

    def search_icd11(self, query):
        return self.client.get("/api/v1/icd/", {"query": query})

    def test_search_no_disease_code(self):
        res = self.search_icd11("14 Diseases of the skin")
        self.assertNotContains(res, "14 Diseases of the skin")

        res = self.search_icd11("Acute effects of ionizing radiation on the skin")
        self.assertNotContains(res, "Acute effects of ionizing radiation on the skin")

    def test_search_with_disease_code(self):
        res = self.search_icd11("aCuTe radiodermatitis following radiotherapy")
        self.assertContains(res, "EL60 Acute radiodermatitis following radiotherapy")

        res = self.search_icd11("cutaneous reactions")
        self.assertContains(res, "EK50.0 Cutaneous insect bite reactions")

        res = self.search_icd11("Haemorrhage rectum")
        self.assertContains(res, "ME24.A1 Haemorrhage of anus and rectum")

        res = self.search_icd11("ME24.A1")
        self.assertContains(res, "ME24.A1 Haemorrhage of anus and rectum")

        res = self.search_icd11("CA22.Z")
        self.assertContains(res, "CA22.Z Chronic obstructive pulmonary disease")

        res = self.search_icd11("1A00 Cholera")
        self.assertContains(res, "1A00 Cholera")

    def test_get_icd11_by_valid_id(self):
        res = self.client.get("/api/v1/icd/133207228/")
        self.assertEqual(
            res.data["label"], "CA22 Chronic obstructive pulmonary disease"
        )

    def test_get_icd11_by_invalid_id(self):
        res = self.client.get("/api/v1/icd/invalid/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
