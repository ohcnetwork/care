from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import Skill
from care.utils.tests.test_utils import TestUtils


class FacilityUserTest(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.skill1 = Skill.objects.create(name="Skill 1")
        cls.skill2 = Skill.objects.create(name="Skill 2")
        cls.user.skills.add(cls.skill1, cls.skill2)

    def test_get_queryset_with_prefetching(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/get_users/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNumQueries(2)
