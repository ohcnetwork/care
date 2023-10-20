from rest_framework.test import APITestCase

from care.users.models import UserFacilityAllocation
from care.utils.tests.test_utils import TestUtils


class TestUserFacilityAllocation(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)

    def setUp(self) -> None:
        # disable force auth
        pass

    def test_user_facility_allocation_is_created_when_user_is_created(self):
        user = self.create_user(
            district=self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        self.assertTrue(UserFacilityAllocation.objects.filter(user=user).exists())

    def test_user_facility_allocation_is_ended_when_home_facility_is_cleared(self):
        user = self.create_user(
            district=self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        user.home_facility = None
        user.save()
        allocation = UserFacilityAllocation.objects.get(
            user=user, facility=self.facility
        )
        self.assertIsNotNone(allocation.end_date)

    def test_user_facility_allocation_is_ended_when_user_is_deleted(self):
        user = self.create_user(
            district=self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        user.deleted = True
        user.save()
        allocation = UserFacilityAllocation.objects.get(
            user=user, facility=self.facility
        )
        self.assertIsNotNone(allocation.end_date)

    def test_user_facility_allocation_on_home_facility_changed(self):
        user = self.create_user(
            district=self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        new_facility = self.create_facility(
            self.super_user, self.district, self.local_body
        )
        user.home_facility = new_facility
        user.save()
        allocation = UserFacilityAllocation.objects.get(
            user=user, facility=self.facility
        )
        self.assertIsNotNone(allocation.end_date)
        self.assertTrue(
            UserFacilityAllocation.objects.filter(
                user=user, facility=new_facility
            ).exists()
        )

    def test_user_facility_allocation_is_not_created_when_user_is_created_without_home_facility(
        self,
    ):
        user = self.create_user(
            district=self.district, username="facility_allocation_test_user"
        )
        self.assertFalse(UserFacilityAllocation.objects.filter(user=user).exists())

    def test_user_facility_allocation_is_not_changed_when_update_fields_is_passed_without_home_facility(
        self,
    ):
        user = self.create_user(
            district=self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        user.save(update_fields=["last_login"])
        self.assertEqual(UserFacilityAllocation.objects.filter(user=user).count(), 1)
