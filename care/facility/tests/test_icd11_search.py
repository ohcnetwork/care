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

        res = self.search_icd11("cutaneous insect bite reactions")
        self.assertContains(res, "EK50.0 Cutaneous insect bite reactions")

        res = self.search_icd11("Haemorrhage of anus and rectum")
        self.assertContains(res, "ME24.A1 Haemorrhage of anus and rectum")

        res = self.search_icd11("ME24.A1")
        self.assertContains(res, "ME24.A1 Haemorrhage of anus and rectum")
