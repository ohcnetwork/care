import datetime

from django.test import TestCase
from freezegun import freeze_time

from care.facility.svc.schedule import (
    get_appointment_slots_for_resource,
)
from care.facility.tests.schedule.setup import ScheduleTestSetup
from care.utils.tests.test_utils import TestUtils


@freeze_time("2024-11-01")
class TestAvailability(TestUtils, ScheduleTestSetup, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.setup_schedule()

    def test_get_appointment_slots(self):
        # considering date as 2024-11-18 Monday
        slot_range = (
            datetime.datetime(2024, 11, 18, 0, 0, 0),
            datetime.datetime(2024, 11, 18, 23, 59, 59),
        )
        slots = get_appointment_slots_for_resource(
            self.schedulable_resource, slot_range[0], slot_range[1]
        )
        self.assertEqual(len(slots), 4)

    def test_get_appointment_slots_with_closed_exception(self):
        # considering date as 2024-11-05 Monday
        slot_range = (
            datetime.datetime(2024, 11, 5, 0, 0, 0),
            datetime.datetime(2024, 11, 5, 23, 59, 59),
        )
        slots = get_appointment_slots_for_resource(
            self.schedulable_resource, slot_range[0], slot_range[1]
        )
        self.assertEqual(len(slots), 0)

    def test_get_appointment_slots_with_open_exception(self):
        # considering date as 2024-11-09 Saturday
        slot_range = (
            datetime.datetime(2024, 11, 9, 0, 0, 0),
            datetime.datetime(2024, 11, 9, 23, 59, 59),
        )
        slots = get_appointment_slots_for_resource(
            self.schedulable_resource, slot_range[0], slot_range[1]
        )
        self.assertEqual(len(slots), 4)
