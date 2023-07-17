from care.users.models import User, UserFacilityAllocation
from care.utils.tests.test_base import TestBase


class TestUserFacilityAllocation(TestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_facility = cls.create_facility(cls.district)

    @classmethod
    def tearDownClass(cls):
        cls.new_facility.delete()
        super().tearDownClass()

    def tearDown(self):
        super().tearDown()
        User._base_manager.filter(username="facility_allocation_test_user").delete()
        UserFacilityAllocation.objects.all().delete()

    def test_user_facility_allocation_is_created_when_user_is_created(self):
        user = self.create_user(
            self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        self.assertTrue(UserFacilityAllocation.objects.filter(user=user).exists())

    def test_user_facility_allocation_is_ended_when_home_facility_is_cleared(self):
        user = self.create_user(
            self.district,
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
            self.district,
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
            self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        user.home_facility = self.new_facility
        user.save()
        allocation = UserFacilityAllocation.objects.get(
            user=user, facility=self.facility
        )
        self.assertIsNotNone(allocation.end_date)
        self.assertTrue(
            UserFacilityAllocation.objects.filter(
                user=user, facility=self.new_facility
            ).exists()
        )

    def test_user_facility_allocation_is_not_created_when_user_is_created_without_home_facility(
        self,
    ):
        user = self.create_user(self.district, username="facility_allocation_test_user")
        self.assertFalse(UserFacilityAllocation.objects.filter(user=user).exists())

    def test_user_facility_allocation_is_not_changed_when_update_fields_is_passed_without_home_facility(
        self,
    ):
        user = self.create_user(
            self.district,
            username="facility_allocation_test_user",
            home_facility=self.facility,
        )
        user.save(update_fields=["last_login"])
        self.assertEqual(UserFacilityAllocation.objects.filter(user=user).count(), 1)
